# Analytics Guide

Shop-scoped analytics power funnel, revenue, lost-demand, and agent-performance views in the admin panel.

## Endpoints (under `/api/v1/shops/{shop_id}/analytics/`)

| Route | Purpose |
|-------|---------|
| `funnel` | Conversion from inbound → product/variant resolution → draft → payment |
| `post-revenue` | Paid revenue and conversion by Instagram post URL |
| `lost-demand` | Unavailable product, attribute, or variant demand with estimated lost revenue |
| `agent-performance` | Auto-send rate, handoff rate, and operator workload signals |

Use `date_from` / `date_to` query parameters (ISO-8601) to scope metrics.

## Interpretation

- Revenue metrics use **paid** orders, not draft or payment-pending counts.
- Empty results are normal for new shops or narrow date windows.
- Lost-demand rows come from `unavailable_demand_logs` written when variant/stock resolution fails.

See also [analytics-guide.md](analytics-guide.md) for operator-facing detail.
