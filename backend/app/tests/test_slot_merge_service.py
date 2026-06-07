from uuid import uuid4

from app.domain.models import ConversationSlots
from app.domain.enums import AgentIntent
from app.schemas.agent import AgentExtractionResult, ExtractedSlots, ExtractionConfidence, ProductReference
from app.services.slot_merge_service import merge_extracted_slots


def test_merge_extracted_slots_preserves_existing_and_fills_new() -> None:
    slots = ConversationSlots(
        conversation_id=uuid4(),
        color="red",
        size=None,
        quantity=1,
        missing_fields=[],
        confidence={},
    )
    extraction = AgentExtractionResult(
        intent=AgentIntent.PROVIDE_INFO,
        product_reference=ProductReference(instagram_post_url="https://instagram.com/p/abc"),
        slots=ExtractedSlots(size="L", phone="09120000000"),
        missing_fields=["customer_name"],
        confidence=ExtractionConfidence(intent=0.9, slots=0.8, product=0.7),
    )

    merged = merge_extracted_slots(slots, extraction)

    assert merged.color == "red"
    assert merged.size == "L"
    assert merged.quantity == 1
    assert merged.phone == "09120000000"
    assert merged.instagram_post_url == "https://instagram.com/p/abc"
    assert merged.missing_fields == ["customer_name"]
    assert merged.confidence["slots"] == 0.8
