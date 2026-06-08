from app.domain.enums import MessageChannel, SuggestedReplyGeneratedBy, SuggestedReplyStatus
from app.domain.models import AdminAuditLog, Conversation, Customer, InstagramAccount, SuggestedReply
from app.schemas.suggested_reply import SuggestedReplyEditAndSend, SuggestedReplyReject
from app.services.agent_settings_service import AgentSettingsService
from app.schemas.agent_settings import ShopAgentStudioSettingsUpdate
from app.domain.enums import AgentMode
from app.services.suggested_reply_service import SuggestedReplyService


def _conversation(db_session, demo_shop):
    account = InstagramAccount(
        shop_id=demo_shop.id,
        ig_user_id="ig-shop",
        username="demo_shop",
        access_token_encrypted="token",
    )
    customer = Customer(shop_id=demo_shop.id, instagram_user_id="ig-customer")
    db_session.add_all([account, customer])
    db_session.flush()
    conversation = Conversation(
        shop_id=demo_shop.id,
        instagram_account_id=account.id,
        customer_id=customer.id,
        channel_provider=MessageChannel.INSTAGRAM.value,
    )
    db_session.add(conversation)
    db_session.flush()
    return conversation


def _reply(db_session, demo_shop, conversation):
    reply = SuggestedReply(
        shop_id=demo_shop.id,
        conversation_id=conversation.id,
        suggested_text="Suggested outfit reply",
        generated_by=SuggestedReplyGeneratedBy.AGENT,
    )
    db_session.add(reply)
    db_session.commit()
    db_session.refresh(reply)
    return reply


def test_approve_suggested_reply_sends_and_audits(db_session, demo_shop, admin_user):
    conversation = _conversation(db_session, demo_shop)
    reply = _reply(db_session, demo_shop, conversation)

    result = SuggestedReplyService(db_session).approve_and_send(demo_shop.id, reply.id, admin_user)

    assert result.status == SuggestedReplyStatus.SENT
    assert result.approved_by_user_id == admin_user.id
    assert db_session.query(AdminAuditLog).filter_by(action="reply_approved", entity_id=str(reply.id)).count() == 1


def test_edit_and_send_suggested_reply_sends_edited_text_and_audits(db_session, demo_shop, admin_user):
    conversation = _conversation(db_session, demo_shop)
    reply = _reply(db_session, demo_shop, conversation)

    result = SuggestedReplyService(db_session).edit_and_send(
        demo_shop.id,
        reply.id,
        SuggestedReplyEditAndSend(edited_text="Edited and safe reply"),
        admin_user,
    )

    assert result.status == SuggestedReplyStatus.SENT
    assert result.edited_text == "Edited and safe reply"
    assert db_session.query(AdminAuditLog).filter_by(action="reply_edited", entity_id=str(reply.id)).count() == 1


def test_reject_suggested_reply_audits(db_session, demo_shop, admin_user):
    conversation = _conversation(db_session, demo_shop)
    reply = _reply(db_session, demo_shop, conversation)

    result = SuggestedReplyService(db_session).reject(
        demo_shop.id,
        reply.id,
        SuggestedReplyReject(reason="Tone is wrong"),
        admin_user,
    )

    assert result.status == SuggestedReplyStatus.REJECTED
    assert result.reason == "Tone is wrong"
    assert db_session.query(AdminAuditLog).filter_by(action="reply_rejected", entity_id=str(reply.id)).count() == 1


def test_agent_mode_and_threshold_changes_create_audit_logs(db_session, demo_shop, admin_user):
    payload = ShopAgentStudioSettingsUpdate(
        mode=AgentMode.CONTROLLED_AUTOPILOT,
        confidence_threshold_intent="0.90",
    )

    AgentSettingsService(db_session).update(demo_shop.id, payload, admin_user)

    assert db_session.query(AdminAuditLog).filter_by(action="agent_mode_changed", entity_id=str(demo_shop.id)).count() == 1
    assert db_session.query(AdminAuditLog).filter_by(action="confidence_threshold_changed", entity_id=str(demo_shop.id)).count() == 1
