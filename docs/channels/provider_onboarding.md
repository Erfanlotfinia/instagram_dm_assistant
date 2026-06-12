# Provider onboarding

1. Open **Channel Accounts** in the admin UI.
2. Choose a provider: Instagram, WhatsApp, Telegram, Bale or Rubika.
3. Enter provider-specific identifiers and credentials.
4. Save the channel account; credentials are encrypted before storage.
5. Configure provider webhook URL as `/api/v1/channels/{provider}/webhook`.
6. Use **Webhook test** to confirm the account is visible to the API.

For WhatsApp, configure the phone number ID and verify token. For Telegram-like bot channels, configure bot token and optional webhook secret.
