const providers = ['Instagram', 'WhatsApp', 'Telegram', 'Bale', 'Rubika'];

function Page({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="page-stack"><header className="page-header"><div><p className="eyebrow">Social admin automation</p><h1>{title}</h1><p>Automation-first controls for deterministic handlers, safe LLM fallback, and useful human handoff.</p></div></header>{children}</div>;
}

export function ScenarioCoveragePage() {
  const rows = ['Referenced content', 'Product discovery', 'Orders', 'Payments', 'Shipping', 'Support', 'Marketing/admin'];
  return <Page title="Scenario Coverage"><section className="card"><h2>Coverage matrix</h2><table><thead><tr><th>Group</th><th>Providers</th><th>Status</th><th>Fallbacks</th></tr></thead><tbody>{rows.map((r) => <tr key={r}><td>{r}</td><td>{providers.join(', ')}</td><td>Partially implemented</td><td>Deterministic → LLM → human</td></tr>)}</tbody></table></section></Page>;
}

export function AutomationRulesPage() {
  return <Page title="Automation Rules"><section className="card"><h2>Handler priority</h2><ol><li>Button/callback payloads</li><li>Explicit commands</li><li>Active order state</li><li>Active context reference</li><li>Deterministic keyword/rule match</li><li>Catalog query parser</li><li>Structured LLM fallback</li><li>Human handoff</li></ol></section></Page>;
}

export function ScenarioSimulatorPage() {
  return <Page title="Scenario Simulator"><section className="card"><h2>Regression pack</h2><p>Run the 150-scenario social admin pack and inspect step-by-step traces, LLM usage, handoff, and unsafe action counts.</p><button type="button" className="button button--primary">Run scenario pack</button></section></Page>;
}

export function AdminAITasksPage() {
  const tasks = ['Suggest reply', 'Summarize conversation', 'FAQ mining', 'Draft post caption', 'Draft story text', 'Draft campaign message'];
  return <Page title="Admin AI Tasks"><section className="card"><h2>Create approval-gated draft</h2><select aria-label="Task type">{tasks.map((t) => <option key={t}>{t}</option>)}</select><textarea aria-label="Context" placeholder="Product, category, campaign, or conversation context" /><button type="button" className="button button--primary">Generate draft</button><p>No task auto-publishes; every generated output requires admin approval.</p></section></Page>;
}

export function OperatorCorrectionsPage() {
  return <Page title="Operator Corrections"><section className="card"><h2>Correction capture</h2><p>Capture corrected scenario, product, attribute, reference, response, and whether automation/LLM/human was appropriate.</p></section></Page>;
}

export function AutomationSuggestionsPage() {
  return <Page title="Automation Suggestions"><section className="card"><h2>Learning loop</h2><p>Review rule, alias, and regression-test suggestions generated from operator corrections.</p></section></Page>;
}
