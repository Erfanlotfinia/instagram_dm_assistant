# WhatsApp Business Platform / Cloud API adapter

The WhatsApp adapter follows Meta Cloud API conventions:

* Webhooks contain `entry[].changes[].value.messages[]` for inbound messages.
* The account is resolved from `metadata.phone_number_id` when possible.
* The adapter normalizes customer `wa_id`, display profile name, text, media IDs and interactive replies.
* Outbound sends use `POST /{phone-number-id}/messages` with a bearer access token.
* Channel policy tracks a 24-hour customer service window; templates are required outside the window.

## References reviewed

* Meta WhatsApp Cloud API documentation: https://developers.facebook.com/docs/whatsapp/cloud-api
* Meta message send endpoint pattern: `https://graph.facebook.com/{version}/{phone-number-id}/messages`.
