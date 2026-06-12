# Instagram adapter

Instagram remains supported through the existing Meta webhook endpoints while new traffic can use `/api/v1/channels/instagram/webhook`.

* Webhook verification uses Meta verify-token challenge for setup.
* POST security supports `X-Hub-Signature-256` HMAC validation when an app secret is configured.
* Inbound messaging events are normalized through `InstagramProviderAdapter`.
* Existing Instagram account and message tables remain for backward compatibility.
