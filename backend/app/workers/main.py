from __future__ import annotations

import json
import logging
import signal
import sys

import pika

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.metrics import PROCESSED_MESSAGES, QUEUE_LAG
from app.integrations.rabbitmq import RETRY_COUNT_HEADER, RabbitMQPublisher, setup_message_queues
from app.workers.message_consumer import ConversationLockedError, handle_delivery

logger = logging.getLogger(__name__)


class WorkerApp:
    def __init__(self) -> None:
        self.settings = get_settings()
        configure_logging(self.settings)
        self._should_stop = False
        self._connection: pika.BlockingConnection | None = None
        self._channel: pika.adapters.blocking_connection.BlockingChannel | None = None
        self._publisher = RabbitMQPublisher(self.settings)

    def start(self) -> None:
        queue_name = self.settings.rabbitmq_queue_message_received
        parameters = pika.URLParameters(self.settings.rabbitmq_url)
        self._connection = pika.BlockingConnection(parameters)
        self._channel = self._connection.channel()
        setup_message_queues(self._channel, self.settings)
        self._channel.basic_qos(prefetch_count=1)
        self._channel.basic_consume(queue=queue_name, on_message_callback=self._on_message)
        self._update_queue_lag()
        logger.info("Worker listening on queue %s", queue_name)
        self._channel.start_consuming()

    def stop(self) -> None:
        self._should_stop = True
        if self._channel and self._channel.is_open:
            self._channel.stop_consuming()
        if self._connection and self._connection.is_open:
            self._connection.close()
        self._publisher.close()
        logger.info("Worker shutdown complete")

    def _update_queue_lag(self) -> None:
        if self._channel is None:
            return
        try:
            depth = self._channel.queue_declare(
                queue=self.settings.rabbitmq_queue_message_received,
                durable=True,
                passive=True,
            ).method.message_count
            QUEUE_LAG.set(depth)
        except Exception:  # noqa: BLE001
            logger.debug("Unable to read queue depth", exc_info=True)

    def _retry_count(self, properties: pika.spec.BasicProperties | None) -> int:
        if properties is None or not properties.headers:
            return 0
        value = properties.headers.get(RETRY_COUNT_HEADER, 0)
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _on_message(
        self,
        channel: pika.adapters.blocking_connection.BlockingChannel,
        method: pika.spec.Basic.Deliver,
        properties: pika.spec.BasicProperties,
        body: bytes,
    ) -> None:
        retry_count = self._retry_count(properties)
        try:
            handle_delivery(body)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            PROCESSED_MESSAGES.inc()
            self._update_queue_lag()
        except ConversationLockedError:
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        except Exception:
            logger.exception("Worker failed to process message retry_count=%s", retry_count)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            next_retry = retry_count + 1
            if next_retry > self.settings.rabbitmq_max_retries:
                try:
                    payload = json.loads(body.decode("utf-8"))
                except json.JSONDecodeError:
                    payload = {"raw": body.decode("utf-8", errors="replace")}
                self._publisher.publish_to_dlq(payload, next_retry)
            else:
                try:
                    payload = json.loads(body.decode("utf-8"))
                    self._publisher.publish(
                        self.settings.rabbitmq_queue_message_received,
                        payload,
                        retry_count=next_retry,
                    )
                except json.JSONDecodeError:
                    self._publisher.publish_to_dlq({"raw": body.decode("utf-8", errors="replace")}, next_retry)


def main() -> None:
    worker = WorkerApp()

    def _shutdown(_signum, _frame) -> None:
        logger.info("Shutdown signal received")
        worker.stop()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        worker.start()
    except KeyboardInterrupt:
        worker.stop()
    except Exception:
        logger.exception("Worker crashed")
        sys.exit(1)


if __name__ == "__main__":
    main()
