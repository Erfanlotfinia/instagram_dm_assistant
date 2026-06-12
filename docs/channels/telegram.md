# Telegram Bot API adapter

Telegram is implemented as a bot-channel adapter:

* Webhook requests can be validated with `X-Telegram-Bot-Api-Secret-Token` when configured.
* `message`, `edited_message` and `callback_query` updates are normalized.
* Outbound text sends through `sendMessage`.
* Policy requires a known chat ID from a prior interaction or allowed bot context.

## References reviewed

* Telegram Bot API: https://core.telegram.org/bots/api
* Telegram webhook FAQ: https://core.telegram.org/bots/faq
