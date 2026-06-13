# Social admin automation

The product is upgraded toward an automation-first AI social media admin: provider adapters only normalize messages, the central scenario router and handler registry decide deterministic actions, the commerce engine remains channel-independent, and the LLM is used only as a structured fallback.

## Scenario audit summary

| group | status after this sprint | providers |
|---|---|---|
| Referenced content | Partially implemented with context graph, resolver, product-list ordinal selection, and clarification paths | Instagram, WhatsApp, Telegram, Bale, Rubika |
| Product discovery | Partially implemented with deterministic category, brand, attribute, price, availability, similar, cheaper, and best-seller planning | Instagram, WhatsApp, Telegram, Bale, Rubika |
| Orders | Existing deterministic order services remain source of truth; handlers route actions instead of mutating directly | Instagram, WhatsApp, Telegram, Bale, Rubika |
| Payments | Existing payment services remain source of truth; suspicious/receipt flows route to safe handlers or handoff | Instagram, WhatsApp, Telegram, Bale, Rubika |
| Shipping | Existing shipping services remain source of truth; handlers classify address, tracking, cost, and complaint scenarios | Instagram, WhatsApp, Telegram, Bale, Rubika |
| Support | Human request, complaint, spam/abuse, policy, return, and exchange handlers are registered | Instagram, WhatsApp, Telegram, Bale, Rubika |
| Marketing/admin | Approval-gated admin tasks support reply, summary, FAQ, caption, story, campaign, announcement, recovery, comparison drafts | Admin UI |

## Coverage matrix source

The live API `GET /api/v1/shops/{shop_id}/scenario-coverage` returns 70 scenario rows with status, deterministic handler availability, LLM fallback, human handoff, test, frontend, and priority fields.
