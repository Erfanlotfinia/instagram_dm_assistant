# Modira Admin UI — Design Guide

Use this document when redesigning the **React admin app** (`frontend/`). It maps product behavior, routes, roles, domain states, and API contracts to screen-level requirements.

**Companion docs:** [api-documentation.md](./api-documentation.md) (every endpoint), [operator-guide.md](./operator-guide.md) (daily workflows), [admin-guide.md](./admin-guide.md) (configuration).

---

## Product summary

Modira is a **multi-channel commerce command center** for operators and admins. Inbound messages from Instagram, WhatsApp, Telegram, Bale, and Rubika flow through automation-first handling; humans take over when confidence is low, policies block auto-send, or customers need help.

**Design principles implied by the codebase:**

1. **Automation-first, human when needed** — show agent state, confidence, and suggested replies before raw message lists.
2. **Commerce context always visible** — product, variant, order, and payment state belong beside the thread, not buried in settings.
3. **Deterministic before LLM** — resolver traces, decision traces, and policy checks are first-class UI surfaces.
4. **Shop-scoped tenancy** — shop switcher in shell; every data view is per shop.
5. **Role-gated hubs** — operators see inbox/orders/catalog/analytics; admins additionally see automation, AI control, and system.

---

## Personas & roles

| Persona | Global role | Shop role | Primary hubs |
|---------|-------------|-----------|--------------|
| Operator | `operator` | `operator` | Overview, Inbox, Handoffs, Orders, Catalog (read/write), Analytics |
| Shop admin | `admin` | `admin` | All operator hubs + Automation, AI Control, System |
| Owner | `owner` | `owner` | Same as admin |

Shell badges (sidebar):

| Badge key | Hub | Data source |
|-----------|-----|-------------|
| `handoffs` | Handoffs | Conversations with `handoff_required` / pending handoff |
| `failedJobs` | System | Failed job count for shop |

---

## Information architecture

Primary navigation is defined in `frontend/src/components/shell/navConfig.tsx`.

```
App shell
├── Shop switcher (TopBar)
├── Sidebar hubs
└── Hub sub-tabs (HubLayout) where applicable

/                     Overview (dashboard KPIs + trends)
/login                Auth (no shell)
/profile              User profile

/inbox                Unified inbox (list + detail split)
/inbox/:id            Same page, detail selected
/inbox/:id/intelligence  Conversation intelligence (decision trace deep-dive)

/handoffs             Handoff queue (priority-sorted triage)

/orders               Orders hub (list)
/orders/:orderId      Order detail + timeline + actions

/catalog/*            Catalog hub
  /products           Product list
  /products/:id       Product detail + variants
  /attributes         Attribute dictionary (color/size aliases)
  /resolver           Variant resolver test bench
  /mapping            Instagram post → product mapping

/automation/*         Automation hub (admin+)
  /rules              Automation rule steps (read-only catalog)
  /coverage           Scenario coverage matrix (~70 scenarios)
  /triggers           Keyword trigger rules
  /recovery           Abandoned payment recovery rules
  /upsell             Product upsell rules
  /simulator          DM simulator (test orchestrator)
  /scenario-simulator Scenario batch simulator
  /risk               Agent risk & confidence thresholds

/ai/*                 AI Control hub (admin+)
  /overview           AI ops summary
  /logs                 LLM call logs
  /fallbacks          Fallback policy view
  /safety             Safety / policy gates
  /corrections        Operator corrections
  /tasks              Admin AI tasks (approve/reject)

/analytics/*          Analytics hub
  /overview           Funnel + performance
  /revenue            Post-attributed revenue
  /demand             Unavailable / lost demand
  /channels           Channel-level metrics

/system/*             System hub (admin+)
  /health             Dependency readiness
  /jobs               Failed jobs (retry/ignore)
  /channels           Channel accounts + connect flows
  /shops              Shop CRUD + members
  /rollout            Pilot control, readiness, onboarding, TRL, incidents
  /settings           Shop + agent settings

/incidents            Incident timeline (also under rollout ?view=incidents)
```

### Routes not in primary nav (design gaps)

| Page component | Status | Recommendation |
|----------------|--------|----------------|
| `CatalogCopilotPage` | Implemented, **not routed** | Add under Catalog hub or merge into products/import UX |
| `SemanticSearchPage` | Implemented, **not routed** | Add under Catalog or AI Control (admin tool) |
| Legacy `/conversations/*` | Redirects to `/inbox` | Remove from any external links |

Rollout sub-views (`/system/rollout?view=`):

| View | Page | Purpose |
|------|------|---------|
| `control` | Pilot Control Center | Emergency stop, resume, pilot settings |
| `readiness` | Pilot Readiness | Pre-launch checklist scores |
| `onboarding` | Onboarding | Shop setup wizard |
| `incidents` | Incident Timeline | Operational incidents |
| `trl` | TRL Validation | Validation run history + scenarios |

---

## Design system

### Brand tokens

Canonical palette: `brand/04_brand_tokens/modira-brand-tokens.css`

| Token | Hex | Usage |
|-------|-----|--------|
| `--modira-teal` | `#147A81` | Primary accent, active nav, CTAs |
| `--modira-teal-dark` | `#0F5F66` | Accent hover |
| `--modira-navy` | `#102A43` | Headings, dark text |
| `--modira-navy-deep` | `#07182B` | Dark canvas |
| `--modira-cyan` | `#38BDF8` | Focus ring, info highlights |
| `--modira-cream` | `#F8F5EA` | Light surfaces (landing) |

Semantic tokens in `frontend/src/app/globals.css`: `canvas`, `surface`, `surface-sunken`, `fg`, `muted`, `accent`, `success`, `warning`, `danger`, `info` — each with `-soft` variants. Theme via `data-theme` on `<html>` (light/dark).

### Layout patterns

| Pattern | Where used |
|---------|------------|
| **App shell** | Fixed sidebar + top bar + scrollable main |
| **Hub tabs** | Horizontal sub-nav under page title (Catalog, Automation, AI, Analytics, System) |
| **Master–detail split** | Inbox (`360px` list + detail), Handoffs (queue + context packet) |
| **Page header** | Eyebrow label (accent uppercase) + title + description |
| **KPI cards** | Overview, analytics dashboards |
| **Card + table** | Lists (orders, products, jobs) |
| **Empty state** | Centered icon + title + helper text |
| **Toast** | Mutation feedback (take-over, send, retry job) |

### Logo assets (admin)

| Context | Asset path |
|---------|------------|
| Sidebar / login (light) | `public/brand/modira_logo_horizontal_full_color.svg` |
| Dark header | `modira_symbol_white.svg` or horizontal white reversed |
| Favicon | `public/favicon.ico`, `favicon.svg` |

---

## Domain states (UI labels & colors)

Design consistent badges/chips for these enums (`backend/app/domain/enums.py`).

### Conversation

| Field | Values | UI notes |
|-------|--------|----------|
| `state` | `open`, `closed`, `pending_handoff`, `archived` | Filter + row status |
| `priority_level` | `urgent`, `high`, `medium`, `low` | Color-coded badge; sort by score |
| `agent_workflow_state` | `idle`, `waiting_for_product`, `waiting_for_variant`, `waiting_for_customer_info`, `waiting_for_confirmation`, `waiting_for_payment`, `paid`, `sent_to_shipping`, `completed`, `cancelled`, `human_handoff` | Pipeline step indicator |
| `is_simulation` | boolean | Distinct visual (e.g. dashed border, “Sim” chip) |
| `handoff_required` | boolean | Drives Handoffs hub badge |
| `preview_required` | boolean | Show suggested reply approval UI |
| `response_mode` | operator vs agent | Toggle after take-over |

### Order (correctness model)

Lifecycle for timeline UI and action buttons:

```
DRAFT → WAITING_FOR_CLARIFICATION ⇄ READY_FOR_CONFIRMATION → RESERVED
  → PAYMENT_PENDING → PAID → ORDER_CREATED
Terminal: FAILED, CANCELLED, EXPIRED
```

Show **allowed next actions** from API/policy, not all buttons always enabled.

### Channel

| Provider | Badge label |
|----------|-------------|
| `instagram` | Instagram |
| `whatsapp` | WhatsApp |
| `telegram` | Telegram |
| `bale` | Bale |
| `rubika` | Rubika |

Account status: `active`, `disabled`, `pending_validation`, etc. — use on System → Channels cards.

---

## Screen specifications

### Overview (`/`)

**API:** `GET /shops/{id}/dashboard/metrics`, `GET .../dashboard/trends?period=7d|30d`

**Content blocks:**

- KPI row: active conversations, pending handoffs, unpaid orders, failed jobs (links to hubs)
- Trend charts: messages, automation vs LLM vs handoff, conversions
- Period toggle: 7d / 30d
- Quick links to Inbox (filtered), Handoffs, Orders

**Empty/new shop:** zeros with copy pointing to onboarding (`/system/rollout?view=onboarding`).

---

### Inbox (`/inbox`)

**API:** `GET /shops/{id}/conversations` (rich filters), `GET .../conversations/{id}`, message/send/handoff endpoints.

**Layout:** List (360px) + detail panel; mobile = list OR detail.

**List columns / chips:**

- Channel badge, customer name/handle
- Priority badge + reason
- Intent snippet, product title if resolved
- Last message time, automation status
- Simulation flag

**Filters (must expose in UI):**

`state`, `handoff_required`, `assigned_to_me`, `unassigned`, `urgent`, `high_priority`, `needs_attention`, `waiting_for_payment`, `ready_to_order`, `low_confidence`, `is_simulation`, `search` (name, phone, IG id, order id, product title).

**Detail panel sections:**

1. Message thread (inbound/outbound, operator vs agent labeled)
2. Suggested reply panel when `preview_required`
3. Manual compose (operator+ only, after take-over)
4. Customer profile sidebar: preferences, order history, inline edit
5. Quick actions: Take over, Release to agent, Assign, Mark resolved, Create order
6. Link to **Intelligence** view for full decision trace

**Rate limit UX:** outbound send shows friendly error on `429`.

---

### Handoffs (`/handoffs`)

Focused triage queue: same conversations as inbox but default-filtered to handoff/priority. Show **wait time** since escalation. Context packet: thread preview + take-over + resolve without full inbox chrome.

---

### Conversation intelligence (`/inbox/:id/intelligence`)

Deep dive: agent decision traces, resolver traces, slot extraction, policy evaluation results. For debugging and operator training—not daily triage.

**API:** decision-traces, assembled traces, resolve trace by id.

---

### Orders hub & detail

**List API:** `GET /shops/{id}/orders` — filters: `status`, `payment_status`, `shipping_status`, date range.

**Detail API:** shop-scoped order read + `/api/v1/orders/{id}/timeline` for correctness timeline.

**Operator actions (detail):** Confirm, Cancel, Send payment link, Mark paid, Ship, Send tracking, Stop recovery.

**Design:** Timeline component mapping `OrderCorrectnessAction` entries; payment status chip; link back to source conversation.

---

### Catalog hub

| Tab | Screen focus | Key API |
|-----|--------------|---------|
| Products | CRUD table, stock, variant count | `/shops/{id}/products` |
| Product detail | Variants table, archive, edit | variants sub-routes |
| Attributes | Color/size alias dictionaries | `/shops/{id}/color-aliases`, `size-aliases` |
| Resolver | Test bench: message → variant result + trace | `POST .../variant-resolver/test` |
| Mapping | IG post URL ↔ products (multi-map per post) | instagram-product-maps |

**Catalog intelligence (admin flows):** import/reindex via `/api/v1/catalog/import`, `/reindex`; normalized list at `/catalog/products`. Consider surfacing import job progress in UI.

**Gap:** `CatalogCopilotPage` and `SemanticSearchPage` exist but need nav entries for import assist and vector search.

---

### Automation hub

| Tab | Purpose |
|-----|---------|
| Rules | Read-only automation step catalog |
| Coverage | 70-row scenario matrix from `GET .../scenario-coverage` |
| Triggers | CRUD keyword rules + performance |
| Recovery | Cart/payment recovery rule CRUD |
| Upsell | Cross-sell rule CRUD |
| Simulator | Fake customer message → orchestrator run (never sends real DM) |
| Scenario simulator | Batch regression runs |
| Risk | Confidence thresholds, handoff flags, high-value preview |

**Simulator output to display:** intent, slots, product/variant resolution, inventory, next state, suggested reply, handoff/preview decision.

---

### AI Control hub

| Tab | Purpose |
|-----|---------|
| Overview | Summary metrics |
| LLM Logs | Historical LLM calls |
| Fallbacks | When LLM is allowed vs blocked |
| Safety | Policy gate configuration preview |
| Corrections | Operator correction feed + submit |
| Tasks | Admin tasks: approve/reject AI-drafted content |

Tasks and suggestions use approve/reject pattern with audit trail.

---

### Analytics hub

| Tab | Metrics | API route |
|-----|---------|-----------|
| Overview | Funnel, agent/operator performance, response time | `/analytics/funnel`, `agent-performance`, `operator-performance`, `response-time` |
| Revenue | Paid revenue by Instagram post | `/analytics/post-revenue` |
| Demand | Unavailable SKU/attribute demand, lost revenue | `/analytics/unavailable-demand`, `lost-demand` |
| Channels | Handoff + channel breakdown | `/analytics/handoff`, related |

**Rules:** revenue = **paid** orders only; empty charts normal for new shops; date range picker (`date_from` / `date_to`).

---

### System hub

| Tab | Purpose |
|-----|---------|
| Health | Postgres, Redis, RabbitMQ, Qdrant, LLM config status |
| Failed Jobs | Paginated DLQ viewer; retry/ignore (admin+); masked payloads |
| Channels | Account list; connect Instagram/Telegram; credential validate |
| Shops | Multi-shop management |
| Rollout | Pilot, onboarding, TRL, incidents (tabbed sub-views) |
| Settings | Shop settings, agent settings, currency, language (`fa` default for IR pilots) |

**Instagram connect flow:** start → OAuth callback → select account → readiness checklist.

**Telegram connect flow:** BYO bot token or managed bot deep link; business mode sync/validate.

---

## Key user flows (wireframe-level)

### 1. Morning operator triage

```
Login → Select shop → Overview (scan KPIs)
  → Handoffs (badge) → Take over → Reply / approve suggested reply
  → Release to agent OR Mark resolved
```

### 2. Payment completion

```
Inbox filter: waiting_for_payment → Open thread
  → Orders panel → Mark paid OR customer pays mock/real link
  → Ship + tracking message
```

### 3. Catalog gap

```
Analytics Demand tab → see unavailable requests
  → Catalog Attributes (add alias) OR Mapping (add post URL)
  → Automation Simulator → verify resolution
```

### 4. Admin pilot launch

```
System Rollout → Onboarding checklist
  → Readiness score → Pilot Control (enable scope)
  → TRL validation run → review failures
  → Emergency stop available on incident
```

---

## Realtime & polling

- **WebSocket:** `/api/v1/ws/shops/{shop_id}` — events: `message.created`, `conversation.updated`, `ping`
- **Overview metrics:** 30s refetch interval in current UI
- Design for connection loss: subtle “live” indicator + manual refresh

---

## Accessibility & i18n notes

- Admin UI is **English** in code strings; operators often work in **Persian (fa)** customer messages — preserve RTL in message bubbles when content is RTL.
- Persian commerce copy appears in payment confirmation templates (backend).
- Focus rings use `--modira-cyan`; maintain contrast on `accent-soft` active nav states.
- Logo alt: “Modira home” when linked.

---

## API quick reference by screen

Full list: [api-documentation.md](./api-documentation.md).

| Screen | Primary endpoints |
|--------|-------------------|
| Overview | `/shops/{id}/dashboard/*` |
| Inbox | `/shops/{id}/conversations/*` |
| Orders | `/shops/{id}/orders/*`, `/orders/{id}/timeline` |
| Catalog | `/shops/{id}/products/*`, `/catalog/*`, `/resolve/*` |
| Automation | `/triggers`, `/recovery-rules`, `/product-upsells`, `/simulator/*` |
| AI Control | `/admin-tasks`, `/operator-corrections`, `/automation-suggestions` |
| Analytics | `/shops/{id}/analytics/*` |
| System | `/ready`, `/failed-jobs`, `/shops/{id}/channels/*`, `/pilot-*` |

---

## Redesign checklist

- [ ] Align sidebar hubs with `navConfig.tsx` (add missing Catalog Copilot / Semantic Search if product wants them)
- [ ] Unify priority/handoff/automation badges across Inbox and Handoffs
- [ ] Order detail timeline matches correctness state machine
- [ ] Rollout sub-views use hub tabs instead of query-param buttons (optional IA improvement)
- [ ] Empty states for each analytics tab with date-range guidance
- [ ] Channel connect flows as stepped wizards with clear error states from OAuth
- [ ] Simulation conversations visually distinct everywhere
- [ ] Mobile inbox master–detail breakpoints documented in design specs
- [ ] Dark mode token parity (landing + admin share brand CSS)

---

## Related architecture (backend context for designers)

| Topic | Doc |
|-------|-----|
| Order state machine | [order-correctness-architecture.md](./order-correctness-architecture.md) |
| Catalog + resolver | [catalog-intelligence-architecture.md](./catalog-intelligence-architecture.md) |
| Channel adapters | [channels-guide.md](./channels-guide.md) |
| Scenario automation | [scenarios/social_admin_automation.md](./scenarios/social_admin_automation.md) |
| DM simulator | [simulator-guide.md](./simulator-guide.md) |
