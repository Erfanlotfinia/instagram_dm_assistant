from unittest.mock import MagicMock

from app.integrations.redis_lock import ConversationLockService


def test_conversation_lock_acquire_and_release() -> None:
    redis_client = MagicMock()
    redis_client.set.return_value = True
    redis_client.eval.return_value = 1

    service = ConversationLockService(redis_client=redis_client)
    token = service.acquire("conv-123", ttl_seconds=30)

    assert token is not None
    redis_client.set.assert_called_once_with("conversation:conv-123:lock", token, nx=True, ex=30)

    released = service.release("conv-123", token)
    assert released is True


def test_conversation_lock_acquire_fails_when_busy() -> None:
    redis_client = MagicMock()
    redis_client.set.return_value = None

    service = ConversationLockService(redis_client=redis_client)
    token = service.acquire("conv-123")

    assert token is None
