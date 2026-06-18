from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import ChannelProvider
from app.domain.models import ChannelAccount


def get_instagram_channel_account_id(db: Session, instagram_account_id: UUID) -> UUID:
    account_id = db.scalar(
        select(ChannelAccount.id).where(
            ChannelAccount.provider == ChannelProvider.INSTAGRAM,
            ChannelAccount.settings_json["legacy_instagram_account_id"].astext
            == str(instagram_account_id),
        )
    )
    if account_id is None:
        raise ValueError(
            f"Instagram account {instagram_account_id} has no matching channel account"
        )
    return account_id
