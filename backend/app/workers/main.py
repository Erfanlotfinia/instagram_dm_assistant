from __future__ import annotations

import logging
import signal
import sys
from typing import Any
from uuid import uuid4

import pika

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.metric_labels import WorkerDlqReason, WorkerRetryReason
from app.core.metrics import (
    record_processed_message,
    record_queue_dlq,
    record_queue_lag,
    record_queue_retry,
)
from app.integrations.rabbitmq import RETRY_COUNT_HEADER, RabbitMQPublisher, setup_message_queues
from app.services.failed_job_service import FailedJobService, format_traceback
from app.workers.message_consumer import (
    ConversationLockedError,
    InvalidJobPayloadError,
    handle_delivery,
    parse_delivery_body,
    validate_message_received_payload,
)

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
        queue_names = [self.settings.rabbitmq_queue_message_received]
        parameters = pika.URLParameters(self.settings.rabbitmq_url)
        self._connection = pika.BlockingConnection(parameters)
        self._channel = self._connection.channel()
        setup_message_queues(self._channel, self.settings)
        self._channel.basic_qos(prefetch_count=1)
        for queue_name in queue_names:
            self._channel.basic_consume(queue=queue_name, on_message_callback=self._on_message)
        self._update_queue_lag()
        logger.info("Worker listening on queues %s", ", ".join(queue_names))
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
            record_queue_lag(self.settings.rabbitmq_queue_message_received, depth)
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
        metadata = self._message_metadata(properties, retry_count)
        try:
            handle_delivery(body)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            self._record_processed(body)
            self._update_queue_lag()
        except ConversationLockedError as exc:
            next_retry = retry_count + 1
            if next_retry > self.settings.rabbitmq_max_retries:
                logger.error(
                    "Conversation lock retry limit exceeded retry_count=%s correlation_id=%s",
                    next_retry,
                    metadata["correlation_id"],
                )
                payload = self._payload_from_body(body)
                reason = f"Conversation lock retry limit exceeded: {exc}"
                self._publish_dlq_then_ack(
                    channel,
                    method,
                    payload,
                    next_retry,
                    reason,
                    metadata,
                    WorkerDlqReason.CONVERSATION_LOCK_EXHAUSTED,
                )
                self._persist_failed_job(payload, next_retry, exc)
            else:
                logger.info(
                    "Conversation locked; delayed retry retry_count=%s correlation_id=%s",
                    next_retry,
                    metadata["correlation_id"],
                )
                self._publish_retry_then_ack(
                    channel,
                    method,
                    body,
                    retry_count,
                    str(exc),
                    metadata,
                    WorkerRetryReason.CONVERSATION_LOCKED,
                )
        except InvalidJobPayloadError as exc:
            logger.error(
                "Worker received non-retryable payload retry_count=%s correlation_id=%s: %s",
                retry_count,
                metadata["correlation_id"],
                exc,
            )
            payload = self._payload_from_body(body)
            self._publish_dlq_then_ack(
                channel,
                method,
                payload,
                retry_count,
                str(exc),
                metadata,
                WorkerDlqReason.INVALID_PAYLOAD,
            )
            self._persist_failed_job(payload, retry_count, exc)
        except Exception as exc:
            logger.exception("Worker failed to process message retry_count=%s", retry_count)
            next_retry = retry_count + 1
            payload = self._payload_from_body(body)
            if next_retry > self.settings.rabbitmq_max_retries:
                reason = f"Max retries exceeded: {exc}"
                self._publish_dlq_then_ack(
                    channel,
                    method,
                    payload,
                    next_retry,
                    reason,
                    metadata,
                    WorkerDlqReason.MAX_RETRIES_EXCEEDED,
                )
                self._persist_failed_job(payload, next_retry, exc)
            else:
                self._publish_retry_then_ack(
                    channel,
                    method,
                    body,
                    retry_count,
                    str(exc),
                    metadata,
                    WorkerRetryReason.PROCESSING_ERROR,
                )

    def _record_processed(self, body: bytes) -> None:
        provider = None
        try:
            payload = parse_delivery_body(body)
            provider = validate_message_received_payload(payload).channel_provider
        except Exception:  # noqa: BLE001
            logger.debug("Unable to resolve provider for processed metric", exc_info=True)
        record_processed_message(provider)

    def _publish_retry_then_ack(
        self,
        channel: pika.adapters.blocking_connection.BlockingChannel,
        method: pika.spec.Basic.Deliver,
        body: bytes,
        retry_count: int,
        reason: str,
        metadata: dict[str, Any],
        metric_reason: WorkerRetryReason,
    ) -> None:
        next_retry = retry_count + 1
        payload = self._payload_from_body(body)
        self._publisher.publish_to_retry(
            payload,
            retry_count=next_retry,
            error_reason=reason,
            correlation_id=metadata["correlation_id"],
            message_id=metadata["message_id"],
        )
        channel.basic_ack(delivery_tag=method.delivery_tag)
        record_queue_retry(self.settings.rabbitmq_queue_message_received, metric_reason)
        logger.warning(
            "Published message to retry queue retry_count=%s correlation_id=%s reason=%s",
            next_retry,
            metadata["correlation_id"],
            reason,
        )

    def _publish_dlq_then_ack(
        self,
        channel: pika.adapters.blocking_connection.BlockingChannel,
        method: pika.spec.Basic.Deliver,
        payload: dict[str, Any],
        retry_count: int,
        reason: str,
        metadata: dict[str, Any],
        metric_reason: WorkerDlqReason,
    ) -> None:
        self._publisher.publish_to_dlq(
            payload,
            retry_count=retry_count,
            error_reason=reason,
            correlation_id=metadata["correlation_id"],
            message_id=metadata["message_id"],
        )
        channel.basic_ack(delivery_tag=method.delivery_tag)
        record_queue_dlq(self.settings.rabbitmq_queue_dlq, metric_reason)
        logger.error(
            "Published message to DLQ retry_count=%s correlation_id=%s reason=%s",
            retry_count,
            metadata["correlation_id"],
            reason,
        )

    def _message_metadata(
        self, properties: pika.spec.BasicProperties | None, retry_count: int
    ) -> dict[str, str | int]:
        headers = properties.headers if properties and properties.headers else {}
        correlation_id = properties.correlation_id if properties else None
        message_id = properties.message_id if properties else None
        return {
            "correlation_id": correlation_id or str(uuid4()),
            "message_id": message_id or str(uuid4()),
            "retry_count": retry_count,
            "error_reason": str(headers.get("x-error-reason", "")),
        }

    def _payload_from_body(self, body: bytes) -> dict:
        try:
            return parse_delivery_body(body)
        except InvalidJobPayloadError:
            return {"raw": body.decode("utf-8", errors="replace")}

    def _persist_failed_job(self, payload: dict, retry_count: int, exc: Exception | None) -> None:
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            FailedJobService.record_failure(
                db,
                queue_name=self.settings.rabbitmq_queue_dlq,
                job_type="message_received",
                payload=payload,
                error_message=str(exc) if exc else "Max retries exceeded",
                retry_count=retry_count,
                tb=format_traceback(exc) if exc else None,
                settings=self.settings,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Unable to persist failed job record")
            db.rollback()
        finally:
            db.close()


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
