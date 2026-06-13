from __future__ import annotations
from pydantic import BaseModel, Field, ValidationError

class LLMConfidence(BaseModel):
    scenario: float = 0.0; product_query: float = 0.0; reference: float = 0.0; order: float = 0.0
class LLMReferencedEntity(BaseModel):
    type: str | None = None; raw_text: str | None = None; confidence: float = 0.0
class LLMProductQuery(BaseModel):
    category_raw: str | None = None; brand_raw: str | None = None; attributes_raw: dict = Field(default_factory=dict); price_range_raw: str | None = None; availability_required: bool | None = None
class LLMOrderIntent(BaseModel):
    wants_to_buy: bool = False; quantity: int | None = None; requested_changes: list[str] = Field(default_factory=list)
class LLMSupportIntent(BaseModel):
    complaint: bool = False; human_requested: bool = False; return_or_exchange: bool = False
class LLMContentAdminIntent(BaseModel):
    wants_caption: bool = False; wants_story: bool = False; wants_campaign: bool = False; topic: str | None = None
class LLMFallbackOutput(BaseModel):
    detected_scenario: str = "unknown"; intent: str = "unclear"; referenced_entity: LLMReferencedEntity = Field(default_factory=LLMReferencedEntity); product_query: LLMProductQuery = Field(default_factory=LLMProductQuery); order_intent: LLMOrderIntent = Field(default_factory=LLMOrderIntent); support_intent: LLMSupportIntent = Field(default_factory=LLMSupportIntent); content_admin_intent: LLMContentAdminIntent = Field(default_factory=LLMContentAdminIntent); confidence: LLMConfidence = Field(default_factory=LLMConfidence); needs_clarification: bool = False; clarification_question: str | None = None; needs_human: bool = False; human_reason: str | None = None; safe_response_draft: str | None = None

class LLMFallbackOrchestrator:
    prompt_version = "social-admin-fallback-v1"; schema_version = "LLMFallbackOutput.v1"
    def validate_output(self, data: dict) -> LLMFallbackOutput:
        out = LLMFallbackOutput.model_validate(data)
        if out.order_intent.wants_to_buy and out.safe_response_draft and any(x in out.safe_response_draft.lower() for x in ["paid", "in stock", "$", "تومان"]):
            out.needs_human = True; out.human_reason = "blocked_possible_hallucinated_commerce_fact"; out.safe_response_draft = None
        return out
    def safe_fallback(self, raw: object) -> LLMFallbackOutput:
        try: return self.validate_output(raw if isinstance(raw, dict) else {})
        except ValidationError: return LLMFallbackOutput(needs_human=True, human_reason="invalid_structured_llm_output")
