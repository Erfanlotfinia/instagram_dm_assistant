# Rubika Bot API adapter

Rubika support is modeled as a bot adapter with Rubika-specific receive modes:

* `receiveUpdate` and `receiveInlineMessage` payloads are accepted.
* Telegram-like update payloads are parsed through the shared bot parser.
* Endpoint mode must use HTTPS in production policy checks.

## References reviewed

* Rubika Bot API public endpoint documentation at https://rubika.ir/botapi and community client payload examples were reviewed where available; implementation keeps `receiveUpdate` and `receiveInlineMessage` parsing isolated behind the adapter.
