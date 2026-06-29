# Analytics Guide

Shop-scoped metrics for the **Analytics** hub. API prefix: `/api/v1/shops/{shop_id}/analytics/`. Full endpoint list: [api-documentation.md](./api-documentation.md#analytics).

## Screens → endpoints

| UI tab | Route | API | Shows |
|--------|-------|-----|-------|
| Overview | `/analytics/overview` | `funnel`, `agent-performance`, `operator-performance`, `response-time` | Conversion funnel, automation vs handoff, operator load |
| Revenue | `/analytics/revenue` | `post-revenue`, `posts` | Paid revenue and engagement by Instagram post |
| Demand | `/analytics/demand` | `unavailable-demand`, `lost-demand` | Stock/attribute gaps, estimated lost revenue |
| Channels | `/analytics/channels` | `handoff`, `stock-demand` | Channel handoff patterns, stock pressure |

## Date ranges

Pass `date_from` and `date_to` (ISO-8601) or `start` / `end` on all analytics GET endpoints.

## Interpretation rules

- **Revenue** counts **paid** orders only—not drafts or payment-pending.
- **Lost demand** rows come from resolver/inventory failures logged during conversations.
- **Empty charts** are normal for new shops or narrow date windows; widen range before concluding failure.
- Use paid-order revenue for pilot go/no-go decisions.

## Design notes

- Always show selected date range in the chart header.
- Provide empty-state copy with link to Catalog mapping when demand tab has no data.
- Funnel steps: inbound → product resolved → variant resolved → draft → payment.

See [ui-design-guide.md](./ui-design-guide.md#analytics-hub) for layout context.
