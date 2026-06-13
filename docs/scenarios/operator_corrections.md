# Module documentation

This module follows the social admin automation architecture documented in docs/scenarios/social_admin_automation.md.

* Deterministic automation is attempted before any LLM call.
* LLM output is structured and validated before use.
* Unsafe, low-confidence, cross-shop, payment, inventory, and publishing risks route to human handoff or approval.
* Providers remain normalization-only; Instagram, WhatsApp, Telegram, Bale, and Rubika use the same central logic.
