import { useEffect, useMemo, useState } from 'react';

const channels = ['IG', 'WA', 'TG', 'Bale', 'Rubika'] as const;
const automationStates = ['Automated', 'LLM handled', 'Human required'] as const;

const conversations = [
  { id: 'C-1048', channel: 'IG', name: '@niloofar', message: 'Is the espresso machine available for pickup today?', intent: 'price', status: 'Automated', product: 'BrewPro X2', sla: '00:18', risk: 'Low' },
  { id: 'C-1047', channel: 'WA', name: 'Reza M.', message: 'Payment failed twice, can someone check?', intent: 'complaint', status: 'Human required', product: 'Order #8411', sla: '02:41', risk: 'High' },
  { id: 'C-1046', channel: 'TG', name: 'Ava Studio', message: 'Need 12 units with invoice and shipping quote.', intent: 'order', status: 'LLM handled', product: 'Bulk quote', sla: '01:08', risk: 'Medium' },
  { id: 'C-1045', channel: 'Rubika', name: 'Customer 8821', message: 'Send catalog for replacement filters.', intent: 'support', status: 'Automated', product: 'Filters', sla: '00:32', risk: 'Low' },
];

const timeline = [
  ['09:42:11', 'Intent router', 'price_request', '0.94 confidence from keyword + product reference'],
  ['09:42:12', 'Catalog resolver', 'BrewPro X2', 'Matched shared post SKU and synonym index'],
  ['09:42:13', 'Scenario handler', 'price_and_stock_v3', 'Deterministic rule covered price + availability'],
  ['09:42:13', 'Decision', 'Automated', 'LLM skipped because all slots were resolved and risk was low'],
];

const kpis = [
  ['Total messages', '18,420', '+12.4%', 'Today / week'],
  ['Automation success', '87.6%', '+3.1%', 'Scenario-first resolution'],
  ['LLM fallback rate', '9.8%', '-1.7%', 'Fallback contained'],
  ['Human handoff rate', '2.6%', '-0.4%', 'Risk escalations'],
  ['Chat → order', '14.2%', '+2.2%', 'Conversion rate'],
  ['Active conversations', '312', '+38', 'Live queues'],
  ['Pending orders', '74', '+9', 'Need payment/shipping'],
  ['Failed jobs', '6', '-3', 'Webhook + queue'],
];

const pages = [
  'Overview dashboard', 'Unified inbox', 'Conversation intelligence', 'Product catalog manager', 'Order management',
  'Automation rules engine', 'AI control center', 'Human handoff queue', 'Analytics & BI', 'System health',
];

function MiniTrend({ tone = 'blue' }: { tone?: 'blue' | 'green' | 'amber' }) {
  const bars = tone === 'green' ? [28, 35, 31, 42, 48, 52, 61] : tone === 'amber' ? [42, 38, 44, 30, 36, 27, 22] : [22, 31, 28, 45, 39, 53, 58];
  return <div className="ed-trend" aria-label="trend chart">{bars.map((height, i) => <span key={i} className={`ed-trend__bar ed-trend__bar--${tone}`} style={{ height }} />)}</div>;
}

function StatusPill({ value }: { value: string }) {
  const tone = value === 'Human required' ? 'danger' : value === 'LLM handled' ? 'warning' : 'success';
  return <span className={`ed-pill ed-pill--${tone}`}>{value}</span>;
}

export function EnterpriseDashboardPage() {
  const [dark, setDark] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [selectedConversation, setSelectedConversation] = useState(conversations[0]);
  const [liveTick, setLiveTick] = useState(128);

  useEffect(() => {
    const timer = window.setInterval(() => setLiveTick((tick) => tick + 1), 5000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setPaletteOpen((open) => !open);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const filteredPages = useMemo(() => pages, []);

  return (
    <div className={dark ? 'enterprise-dashboard enterprise-dashboard--dark' : 'enterprise-dashboard'}>
      <header className="ed-topbar">
        <div>
          <p className="ed-eyebrow">Modira · AI Social Media Admin OS</p>
          <h1>Social commerce operations command center</h1>
          <p>Monitor channels, explain automation decisions, operate catalog → order → payment → shipping.</p>
        </div>
        <div className="ed-actions">
          <button className="ed-command" type="button" onClick={() => setPaletteOpen(true)}>⌘K Search</button>
          <button className="ed-button" type="button" onClick={() => setDark((value) => !value)}>{dark ? 'Light mode' : 'Dark mode'}</button>
          <span className="ed-live">Live · {liveTick} events/min</span>
        </div>
      </header>

      {paletteOpen ? <div className="ed-palette" role="dialog" aria-modal="true"><div className="ed-palette__panel"><input autoFocus placeholder="Jump to page, order, conversation, rule…" onKeyDown={(e) => e.key === 'Escape' && setPaletteOpen(false)} />{filteredPages.map((page) => <button key={page} onClick={() => setPaletteOpen(false)}>{page}<span>Open</span></button>)}</div></div> : null}

      <section className="ed-kpi-grid">{kpis.map(([label, value, delta, hint], index) => <article className="ed-card ed-kpi" key={label}><div><p>{label}</p><strong>{value}</strong><small>{hint}</small></div><span className={delta.startsWith('-') ? 'ed-delta ed-delta--good' : 'ed-delta'}>{delta}</span><MiniTrend tone={index === 2 || index === 3 || index === 7 ? 'amber' : 'green'} /></article>)}</section>

      <main className="ed-grid">
        <section className="ed-card ed-inbox">
          <div className="ed-section-head"><div><h2>Unified inbox</h2><p>Multi-channel queue with automation state, intent, product context, and SLA.</p></div><input aria-label="Filter conversations" placeholder="Filter like Stripe: channel:wa status:human intent:order" /></div>
          <div className="ed-inbox-layout"><div className="ed-conversation-list">{conversations.map((conversation) => <button key={conversation.id} className={selectedConversation.id === conversation.id ? 'ed-conversation ed-conversation--active' : 'ed-conversation'} onClick={() => setSelectedConversation(conversation)}><span className="ed-channel">{conversation.channel}</span><div><strong>{conversation.name}</strong><p>{conversation.message}</p><small>{conversation.intent} · {conversation.product} · SLA {conversation.sla}</small></div><StatusPill value={conversation.status} /></button>)}</div><aside className="ed-thread"><div className="ed-thread__header"><h3>{selectedConversation.name}</h3><StatusPill value={selectedConversation.status} /></div><div className="ed-chat"><p className="ed-bubble ed-bubble--in">{selectedConversation.message}</p><article className="ed-product-card"><b>{selectedConversation.product}</b><span>Stock 42 · demand +18% · linked to 23 chats</span></article><p className="ed-bubble ed-bubble--out">Yes — it is available. I can draft the order and send a secure payment link.</p></div><div className="ed-order-draft"><h4>Order draft</h4><dl><dt>Customer</dt><dd>{selectedConversation.name}</dd><dt>Payment</dt><dd>Pending link</dd><dt>Shipping</dt><dd>Needs address</dd></dl></div></aside></div>
        </section>

        <aside className="ed-card ed-trace"><h2>Scenario trace</h2><p>Answers: why did the system respond this way?</p>{timeline.map(([time, step, result, why]) => <article className="ed-trace-row" key={time}><time>{time}</time><div><strong>{step}</strong><span>{result}</span><p>{why}</p></div></article>)}</aside>
      </main>

      <section className="ed-ops-grid">
        <article className="ed-card"><h2>Conversation intelligence</h2><ul><li>Context graph: customer ↔ product ↔ order ↔ policy</li><li>Referenced product resolution with evidence chain</li><li>Scenario timeline, decision trace, LLM usage, human overrides</li></ul></article>
        <article className="ed-card"><h2>Catalog manager</h2><ul><li>CRUD, variants, attributes, stock, pricing rules, bulk upload</li><li>Industry-agnostic taxonomy and category presets</li><li>Search index status linked to unresolved demand</li></ul></article>
        <article className="ed-card"><h2>Orders & payments</h2><ul><li>Pipeline: draft → confirmed → paid → shipped → resolved</li><li>Retry payment, restricted override, linked conversation audit</li><li>Shipping exceptions and payment reconciliation</li></ul></article>
        <article className="ed-card"><h2>Automation rules engine</h2><ul><li>Priority rules, keywords → actions, intents → handlers</li><li>Simulation mode and test conversation runner</li><li>Override AI behavior with versioned approvals</li></ul></article>
        <article className="ed-card"><h2>AI control center</h2><ul><li>Prompt logs, LLM fallback cases, hallucination detection</li><li>Blocked unsafe actions and policy evaluations</li><li>Training queue from operator corrections</li></ul></article>
        <article className="ed-card"><h2>System health</h2><ul><li>API, DB, RabbitMQ, webhooks, LLM latency</li><li>Error rates with failed-job replay runbooks</li><li>Polling/WebSocket freshness indicators</li></ul></article>
      </section>

      <section className="ed-card ed-spec"><h2>Implementation blueprint</h2><div className="ed-columns"><div><h3>State model</h3><pre>{`Conversation { channel, messages, intent, automationState, productContext, orderId, trace[] }
Order { state, paymentStatus, shippingStatus, conversationId, audit[] }
Rule { priority, matcher, handler, simulationResults, version }
Health { api, queue, db, llmLatency, webhookFailures }`}</pre></div><div><h3>API contracts</h3><pre>{`GET /api/admin/overview?range=today
GET /api/conversations?channel=&intent=&status=
GET /api/conversations/{id}/intelligence
POST /api/rules/{id}/simulate
GET /api/ai/logs?type=fallback|blocked|prompt
WS /ws/ops -> conversation.updated, order.updated, health.alert`}</pre></div><div><h3>UX flow</h3><pre>{`Inbound message → intent/router → scenario handler
  ↳ resolved: auto reply + trace
  ↳ uncertain: LLM fallback + guardrails
  ↳ risky: handoff queue + context packet
Operator correction → training queue → rule/prompt update`}</pre></div></div></section>
    </div>
  );
}
