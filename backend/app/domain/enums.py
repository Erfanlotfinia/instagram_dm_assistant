import enum


class UserRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    OPERATOR = "operator"


class ShopStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class HandoffMode(str, enum.Enum):
    AUTOMATIC = "automatic"
    MANUAL_ONLY = "manual_only"


class InstagramAccountStatus(str, enum.Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    EXPIRED = "expired"


class ConversationState(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    PENDING_HANDOFF = "pending_handoff"
    ARCHIVED = "archived"


class AgentWorkflowState(str, enum.Enum):
    IDLE = "idle"
    WAITING_FOR_PRODUCT = "waiting_for_product"
    WAITING_FOR_VARIANT = "waiting_for_variant"
    WAITING_FOR_CUSTOMER_INFO = "waiting_for_customer_info"
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"
    WAITING_FOR_PAYMENT = "waiting_for_payment"
    PAID = "paid"
    SENT_TO_SHIPPING = "sent_to_shipping"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    HUMAN_HANDOFF = "human_handoff"


class AgentRunStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"


class AgentIntent(str, enum.Enum):
    BUY_PRODUCT = "buy_product"
    ASK_PRICE = "ask_price"
    ASK_STOCK = "ask_stock"
    PROVIDE_INFO = "provide_info"
    CONFIRM_ORDER = "confirm_order"
    CANCEL_ORDER = "cancel_order"
    TRACK_ORDER = "track_order"
    UNCLEAR = "unclear"
    HUMAN_HELP = "human_help"


class MessageDirection(str, enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MessageChannel(str, enum.Enum):
    INSTAGRAM = "instagram"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    WEB_CHAT = "web_chat"


class MessageType(str, enum.Enum):
    TEXT = "text"
    SHARED_POST = "shared_post"
    ATTACHMENT = "attachment"
    SYSTEM = "system"


class AgentActionStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"


class WebhookProvider(str, enum.Enum):
    INSTAGRAM = "instagram"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    WEB_CHAT = "web_chat"


class WebhookProcessingStatus(str, enum.Enum):
    RECEIVED = "received"
    QUEUED = "queued"
    PROCESSED = "processed"
    FAILED = "failed"


class ProductStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class InventoryMovementType(str, enum.Enum):
    RESERVE = "reserve"
    RELEASE = "release"
    SALE = "sale"
    ADJUSTMENT = "adjustment"


class ConfidenceSource(str, enum.Enum):
    MANUAL = "manual"
    CAPTION_MATCH = "caption_match"
    IMAGE_MATCH = "image_match"
    ADMIN_CONFIRMED = "admin_confirmed"


class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    WAITING_FOR_CLARIFICATION = "waiting_for_clarification"
    READY_FOR_CONFIRMATION = "ready_for_confirmation"
    RESERVED = "reserved"
    PAYMENT_PENDING = "payment_pending"
    PAID = "paid"
    ORDER_CREATED = "order_created"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class InventoryReservationStatus(str, enum.Enum):
    ACTIVE = "active"
    CONFIRMED = "confirmed"
    RELEASED = "released"
    EXPIRED = "expired"


class OrderTransitionTrigger(str, enum.Enum):
    API = "api"
    WEBHOOK = "webhook"
    WORKER = "worker"
    SYSTEM = "system"


class OrderCorrectnessAction(str, enum.Enum):
    CREATE_DRAFT = "create_draft"
    CLARIFY = "clarify"
    CONFIRM = "confirm"
    RESERVE = "reserve"
    PAYMENT_LINK = "payment_link"
    COMPLETE = "complete"
    CANCEL = "cancel"
    MARK_PAID = "mark_paid"
    EXPIRE = "expire"


class WebhookDedupeOutcome(str, enum.Enum):
    PROCESSED = "processed"
    DUPLICATE = "duplicate"
    IGNORED = "ignored"


class OperatorReviewDecision(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class OrderPaymentStatus(str, enum.Enum):
    UNPAID = "unpaid"
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class OrderShippingStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    PREPARING = "preparing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"


class PaymentProvider(str, enum.Enum):
    MANUAL = "manual"
    ZARINPAL = "zarinpal"
    NEXTPAY = "nextpay"
    IDPAY = "idpay"
    MOCK = "mock"


class PaymentRecordStatus(str, enum.Enum):
    CREATED = "created"
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ShipmentProvider(str, enum.Enum):
    MANUAL = "manual"
    POST = "post"
    TIPAX = "tipax"
    CHAPAR = "chapar"
    OTHER = "other"


class ShipmentStatus(str, enum.Enum):
    PENDING = "pending"
    PREPARING = "preparing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    FAILED = "failed"


class TriggerSourceType(str, enum.Enum):
    COMMENT = "comment"
    STORY_REPLY = "story_reply"
    REEL_COMMENT = "reel_comment"
    DIRECT_DM = "direct_dm"
    AD_COMMENT = "ad_comment"


class AgentMode(str, enum.Enum):
    COPILOT = "copilot"
    CONTROLLED_AUTOPILOT = "controlled_autopilot"
    HUMAN_FIRST = "human_first"


class SuggestedReplyStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"
    SENT = "sent"


class SuggestedReplyGeneratedBy(str, enum.Enum):
    AGENT = "agent"
    OPERATOR = "operator"


class SellingStyle(str, enum.Enum):
    FRIENDLY = "friendly"
    FORMAL = "formal"
    CONCISE = "concise"
    PROMOTIONAL = "promotional"
    EDUCATIONAL = "educational"
    BALANCED = "balanced"


class ConversationPriorityLevel(str, enum.Enum):
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class OrderRecoveryStatus(str, enum.Enum):
    NONE = "none"
    ELIGIBLE = "eligible"
    IN_PROGRESS = "in_progress"
    RECOVERED = "recovered"
    FAILED = "failed"
    STOPPED = "stopped"


class OrderRecoveryAttemptStatus(str, enum.Enum):
    CREATED = "created"
    SENT = "sent"
    SKIPPED = "skipped"
    FAILED = "failed"


class UpsellSuggestionStatus(str, enum.Enum):
    SUGGESTED = "suggested"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SKIPPED = "skipped"


class FailedJobStatus(str, enum.Enum):
    FAILED = "failed"
    RETRIED = "retried"
    IGNORED = "ignored"


class ConversationEventType(str, enum.Enum):
    INBOUND_MESSAGE = "inbound_message_received"
    OUTBOUND_MESSAGE = "outbound_message_sent"
    SUGGESTED_REPLY_CREATED = "suggested_reply_created"
    SUGGESTED_REPLY_APPROVED = "suggested_reply_approved"
    PRODUCT_RESOLVED = "product_resolved"
    VARIANT_RESOLVED = "variant_resolved"
    INVENTORY_CHECKED = "inventory_checked"
    DRAFT_ORDER_CREATED = "draft_order_created"
    CUSTOMER_INFO_COMPLETED = "customer_info_completed"
    CONFIRMATION_REQUESTED = "confirmation_requested"
    PAYMENT_LINK_SENT = "payment_link_sent"
    PAYMENT_RECEIVED = "payment_received"
    ORDER_SHIPPED = "order_shipped"
    HANDOFF_REQUIRED = "handoff_required"
    OPERATOR_TOOK_OVER = "operator_took_over"
    OPERATOR_RELEASED_AGENT = "operator_released_to_agent"
    ORDER_CANCELLED = "order_cancelled"
    CONVERSATION_ASSIGNED = "conversation_assigned"
    CUSTOMER_PROFILE_UPDATED = "customer_profile_updated"


class PilotEventSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
