from unittest.mock import MagicMock, patch

from app.core.config import Settings
from app.integrations.rabbitmq import setup_message_queues
from app.workers.main import WorkerApp


def test_setup_message_queues_declares_legacy_inbound_topology() -> None:
    channel = MagicMock()
    settings = Settings(app_env="test")

    setup_message_queues(channel, settings)

    declared_queues = [call.kwargs["queue"] for call in channel.queue_declare.call_args_list]
    assert settings.rabbitmq_queue_message_received in declared_queues
    assert settings.rabbitmq_legacy_queue_message_received in declared_queues
    assert settings.rabbitmq_legacy_queue_retry in declared_queues
    assert settings.rabbitmq_legacy_queue_dlq in declared_queues


def test_worker_consumes_configured_and_legacy_inbound_queues() -> None:
    settings = Settings(
        app_env="test",
        rabbitmq_queue_message_received="custom.message.received",
        rabbitmq_queue_retry="custom.message.received.retry",
        rabbitmq_queue_dlq="custom.message.received.dlq",
    )
    channel = MagicMock()
    connection = MagicMock()
    connection.channel.return_value = channel

    with (
        patch("app.workers.main.get_settings", return_value=settings),
        patch("app.workers.main.configure_logging"),
        patch("app.workers.main.RabbitMQPublisher"),
        patch("app.workers.main.pika.BlockingConnection", return_value=connection),
        patch.object(WorkerApp, "_update_queue_lag"),
    ):
        worker = WorkerApp()
        worker.start()

    consumed_queues = [call.kwargs["queue"] for call in channel.basic_consume.call_args_list]
    assert consumed_queues == [
        "custom.message.received",
        "instagram.message.received",
    ]
