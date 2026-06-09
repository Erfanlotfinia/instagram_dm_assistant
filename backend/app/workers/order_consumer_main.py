"""Consumer for order correctness RabbitMQ queues."""

from __future__ import annotations

import json
import logging
import signal

import pika

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.integrations.rabbitmq import setup_message_queues, setup_order_correctness_queues
from app.workers.order_workers import (
    handle_compensation,
    handle_operator_alert,
    handle_payment_callback,
    handle_reservation_expiry,
)

logger = logging.getLogger(__name__)

QUEUE_HANDLERS = {
    "reservation_expiry": handle_reservation_expiry,
    "payment_callbacks": handle_payment_callback,
    "order_compensation": handle_compensation,
    "operator_alerts": handle_operator_alert,
}


def _on_message(queue_name: str, handler_name: str, body: bytes) -> None:
    payload = json.loads(body.decode("utf-8"))
    handler = QUEUE_HANDLERS[handler_name]
    db = SessionLocal()
    settings = get_settings()
    try:
        handler(db, payload, settings)
    except Exception:
        db.rollback()
        logger.exception("Order queue handler failed queue=%s", queue_name)
        raise
    finally:
        db.close()


def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    parameters = pika.URLParameters(settings.rabbitmq_url)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    setup_message_queues(channel, settings)
    setup_order_correctness_queues(channel, settings)

    bindings = {
        settings.rabbitmq_queue_reservation_expiry: "reservation_expiry",
        settings.rabbitmq_queue_payment_callbacks: "payment_callbacks",
        settings.rabbitmq_queue_order_compensation: "order_compensation",
        settings.rabbitmq_queue_operator_alerts: "operator_alerts",
    }

    def callback(ch, method, _properties, body):
        try:
            _on_message(method.routing_key, bindings[method.routing_key], body)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception:
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    for queue_name in bindings:
        channel.basic_consume(queue=queue_name, on_message_callback=callback)
        logger.info("Consuming queue %s", queue_name)

    def shutdown(_signum, _frame):
        channel.stop_consuming()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    channel.start_consuming()


if __name__ == "__main__":
    main()
