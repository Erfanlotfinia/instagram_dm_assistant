from __future__ import annotations

import json
import logging
from typing import Any, Protocol

import pika
from pika.adapters.blocking_connection import BlockingChannel

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

RETRY_COUNT_HEADER = "x-retry-count"


class MessagePublisher(Protocol):
    def publish(self, queue_name: str, payload: dict[str, Any], retry_count: int = 0) -> None:
        ...


def setup_message_queues(channel: BlockingChannel, settings: Settings | None = None) -> None:
    """Declare primary, retry (TTL), and dead-letter queues."""
    settings = settings or get_settings()
    _declare_message_queue_topology(
        channel,
        settings.rabbitmq_queue_message_received,
        settings.rabbitmq_queue_retry,
        settings.rabbitmq_queue_dlq,
        settings.rabbitmq_retry_delay_ms,
    )

    if settings.rabbitmq_legacy_queue_message_received != settings.rabbitmq_queue_message_received:
        _declare_message_queue_topology(
            channel,
            settings.rabbitmq_legacy_queue_message_received,
            settings.rabbitmq_legacy_queue_retry,
            settings.rabbitmq_legacy_queue_dlq,
            settings.rabbitmq_retry_delay_ms,
        )

    setup_order_correctness_queues(channel, settings)
    logger.info(
        "RabbitMQ queues declared main=%s legacy_main=%s",
        settings.rabbitmq_queue_message_received,
        settings.rabbitmq_legacy_queue_message_received,
    )


def _declare_message_queue_topology(
    channel: BlockingChannel,
    main_queue: str,
    retry_queue: str,
    dlq_queue: str,
    retry_delay_ms: int,
) -> None:
    channel.queue_declare(queue=dlq_queue, durable=True)
    channel.queue_declare(
        queue=retry_queue,
        durable=True,
        arguments={
            "x-message-ttl": retry_delay_ms,
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": main_queue,
        },
    )
    channel.queue_declare(
        queue=main_queue,
        durable=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": retry_queue,
        },
    )


def setup_order_correctness_queues(
    channel: BlockingChannel, settings: Settings | None = None
) -> None:
    settings = settings or get_settings()
    dead_letter = settings.rabbitmq_queue_dead_letter
    channel.queue_declare(queue=dead_letter, durable=True)
    for queue_name in (
        settings.rabbitmq_queue_payment_callbacks,
        settings.rabbitmq_queue_reservation_expiry,
        settings.rabbitmq_queue_order_compensation,
        settings.rabbitmq_queue_operator_alerts,
    ):
        channel.queue_declare(
            queue=queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": dead_letter,
            },
        )


def get_queue_depth(channel: BlockingChannel, queue_name: str) -> int:
    method = channel.queue_declare(queue=queue_name, durable=True, passive=True)
    return method.method.message_count


class RabbitMQPublisher:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._connection: pika.BlockingConnection | None = None
        self._channel: BlockingChannel | None = None

    def connect(self) -> None:
        if self._connection and self._connection.is_open:
            return
        parameters = pika.URLParameters(self.settings.rabbitmq_url)
        self._connection = pika.BlockingConnection(parameters)
        self._channel = self._connection.channel()
        setup_message_queues(self._channel, self.settings)
        logger.info("Connected to RabbitMQ")

    def close(self) -> None:
        if self._channel and self._channel.is_open:
            self._channel.close()
        if self._connection and self._connection.is_open:
            self._connection.close()
        self._channel = None
        self._connection = None

    def _ensure_channel(self) -> BlockingChannel:
        if self._channel is None or not self._channel.is_open:
            self.connect()
        assert self._channel is not None
        return self._channel

    def declare_queue(self, queue_name: str) -> None:
        channel = self._ensure_channel()
        channel.queue_declare(queue=queue_name, durable=True)

    def publish(self, queue_name: str, payload: dict[str, Any], retry_count: int = 0) -> None:
        channel = self._ensure_channel()
        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
                headers={RETRY_COUNT_HEADER: retry_count},
            ),
        )
        logger.info("Published message to queue %s retry_count=%s", queue_name, retry_count)

    def publish_to_dlq(self, payload: dict[str, Any], retry_count: int) -> None:
        channel = self._ensure_channel()
        channel.basic_publish(
            exchange="",
            routing_key=self.settings.rabbitmq_queue_dlq,
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
                headers={RETRY_COUNT_HEADER: retry_count},
            ),
        )
        logger.error("Message moved to DLQ after %s retries", retry_count)


class NoOpPublisher:
    def publish(self, queue_name: str, payload: dict[str, Any], retry_count: int = 0) -> None:
        logger.info("No-op publish to %s retry_count=%s: %s", queue_name, retry_count, payload)
