# Bale Bot API adapter

Bale uses a Telegram-like bot model in this foundation:

* Payloads are normalized through the Telegram-compatible parser where possible.
* The adapter uses a Bale-specific API base URL for future outbound calls.
* Policy treats Bale as a bot channel: the shop can message chats that interacted with the bot or are explicitly allowed.

## References reviewed

* Bale Bot API public documentation and Telegram-compatible community clients were reviewed where available; implementation keeps provider-specific endpoint configuration isolated for verification in production onboarding.
