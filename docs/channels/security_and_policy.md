# Channel security and policy

## Security

* Provider access tokens and bot tokens are encrypted at rest.
* Webhook payload logs must be masked for PII and secrets.
* Webhook handlers must not call LLMs inline.
* Deduplication keys combine provider, channel account and external message/update identifiers.

## Policy

* WhatsApp enforces customer-service-window awareness and requires approved templates outside the session window.
* Telegram and Bale only send to known or allowed bot chats.
* Rubika endpoint mode requires HTTPS.
* Instagram keeps existing policy and safety controls.
* Outbound sending remains subject to pilot mode and emergency-stop rules before real provider calls are enabled.
