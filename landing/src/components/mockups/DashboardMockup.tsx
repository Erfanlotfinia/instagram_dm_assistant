import { useState } from 'react';

import { dashboard } from '../../content/site';
import { Badge } from '../ui/Badge';
import { Icon } from '../ui/Icon';
import { DecisionTrace } from './DecisionTrace';
import { OrderStatusCard } from './OrderStatusCard';
import { ProductCard } from './ProductCard';

const tabs = [
  { id: 'inbox', icon: 'Inbox', label: 'این‌باکس' },
  { id: 'context', icon: 'PackageSearch', label: 'زمینهٔ محصول' },
  { id: 'analytics', icon: 'BarChart3', label: 'تحلیل‌ها' },
] as const;

type TabId = (typeof tabs)[number]['id'];

const analytics = [
  { label: 'نرخ اتوماسیون', value: '۷۸٪', icon: 'Workflow', tone: 'cyan' as const },
  { label: 'نرخ تبدیل', value: '۳۱٪', icon: 'TrendingUp', tone: 'emerald' as const },
  { label: 'تحویل به انسان', value: '۹٪', icon: 'UserCheck', tone: 'neutral' as const },
  { label: 'ارجاعات حل‌نشده', value: '۲٪', icon: 'AlertTriangle', tone: 'neutral' as const },
];

const bars = [42, 65, 58, 80, 72, 91, 78];

export function DashboardMockup() {
  const [active, setActive] = useState<TabId>('inbox');

  return (
    <div className="glass-strong overflow-hidden rounded-3xl">
      {/* Top bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
        <span className="flex items-center gap-2 text-sm font-semibold text-fg">
          <Icon name="LayoutDashboard" size={16} className="text-modira-cyan" />
          داشبورد عملیاتی
        </span>
        <div className="flex items-center gap-1.5">
          <Badge tone="cyan">
            <Icon name="Workflow" size={11} /> Automation
          </Badge>
          <Badge tone="emerald">
            <Icon name="Sparkles" size={11} /> LLM
          </Badge>
        </div>
      </div>

      <div className="grid lg:grid-cols-[180px_1fr]">
        {/* Side modules */}
        <nav className="hidden flex-col gap-1 border-e border-border p-3 lg:flex" aria-label="ماژول‌ها">
          {dashboard.modules.map((m) => (
            <span
              key={m.label}
              className="flex items-center gap-2 rounded-xl px-2.5 py-2 text-xs text-fg/80 transition-colors hover:bg-surface-sunken hover:text-fg"
            >
              <Icon name={m.icon} size={14} className="text-modira-cyan/80" />
              {m.label}
            </span>
          ))}
        </nav>

        {/* Main panel */}
        <div className="p-4">
          {/* Tabs */}
          <div role="tablist" aria-label="نمای داشبورد" className="mb-4 flex flex-wrap gap-1.5">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                role="tab"
                aria-selected={active === tab.id}
                onClick={() => setActive(tab.id)}
                className={`flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-medium transition-all ${
                  active === tab.id
                    ? 'accent-gradient text-modira-navy-deep'
                    : 'border border-border bg-surface-sunken text-fg/80 hover:text-fg'
                }`}
              >
                <Icon name={tab.icon} size={13} />
                {tab.label}
              </button>
            ))}
          </div>

          {active === 'inbox' ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2.5 rounded-2xl border border-border bg-surface p-3">
                <p className="text-xs font-semibold text-fg">جزئیات مکالمه</p>
                <div className="rounded-xl bg-surface-sunken p-2 text-xs text-fg/80">
                  «همه چکش‌های برند بوش زیر ۵ میلیون رو بفرست»
                </div>
                <ProductCard name="چکش بوش GBH" price="۳٬۸۰۰٬۰۰۰ تومان" meta="ابزار برقی" compact />
                <ProductCard name="چکش بوش PBH" price="۴٬۵۰۰٬۰۰۰ تومان" meta="ابزار برقی" compact />
              </div>
              <div className="space-y-2.5">
                <DecisionTrace
                  title="ردگیری تصمیم"
                  steps={[
                    { label: 'فیلتر برند: بوش', kind: 'automation' },
                    { label: 'فیلتر قیمت: زیر ۵ میلیون', kind: 'automation' },
                    { label: 'واکشی نتایج از کاتالوگ', kind: 'data' },
                    { label: 'ساخت متن فهرست', kind: 'llm' },
                  ]}
                />
                <OrderStatusCard orderId="#۱۰۹۲" />
              </div>
            </div>
          ) : null}

          {active === 'context' ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2.5 rounded-2xl border border-border bg-surface p-3">
                <p className="text-xs font-semibold text-fg">پیش‌نویس سفارش</p>
                <ProductCard name="کفش رانینگ Aero — سایز ۴۲" price="۲٬۴۵۰٬۰۰۰ تومان" meta="۱ عدد" />
                <div className="flex items-center justify-between rounded-xl bg-surface-sunken p-2 text-xs">
                  <span className="text-muted">جمع کل</span>
                  <span className="ltr font-bold text-modira-cyan">۲٬۴۵۰٬۰۰۰ تومان</span>
                </div>
                <div className="flex items-center gap-1.5 rounded-xl border border-modira-cyan/25 bg-modira-cyan/10 p-2 text-[11px] text-modira-cyan">
                  <Icon name="ClipboardCheck" size={13} />
                  در انتظار تأیید نهایی ادمین
                </div>
              </div>
              <div className="space-y-2.5 rounded-2xl border border-border bg-surface p-3">
                <p className="text-xs font-semibold text-fg">بستهٔ تحویل به انسان</p>
                <ul className="space-y-1.5 text-[11px] text-fg/80">
                  {['خلاصهٔ مکالمه', 'محصول و سفارش مرتبط', 'سطح ریسک: متوسط', 'پیشنهاد پاسخ آماده'].map((x) => (
                    <li key={x} className="flex items-center gap-1.5">
                      <Icon name="Check" size={12} className="text-modira-teal" />
                      {x}
                    </li>
                  ))}
                </ul>
                <div className="flex items-center gap-1.5 rounded-xl border border-border-strong bg-surface-sunken p-2 text-[11px] text-fg">
                  <Icon name="AlertTriangle" size={13} />
                  کارهای ناموفق: ۰ مورد در صف
                </div>
              </div>
            </div>
          ) : null}

          {active === 'analytics' ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
                {analytics.map((a) => (
                  <div key={a.label} className="rounded-2xl border border-border bg-surface p-3">
                    <Icon name={a.icon} size={16} className="text-modira-cyan" />
                    <p className="ltr mt-2 text-xl font-extrabold text-fg">{a.value}</p>
                    <p className="text-[11px] text-muted">{a.label}</p>
                  </div>
                ))}
              </div>
              <div className="rounded-2xl border border-border bg-surface p-3">
                <p className="mb-3 text-xs font-semibold text-fg">عملکرد کانال‌ها در هفته</p>
                <div className="flex h-28 items-end gap-2">
                  {bars.map((h, i) => (
                    <div key={i} className="flex flex-1 flex-col items-center gap-1">
                      <span
                        className="w-full rounded-t-md accent-gradient"
                        style={{ height: `${h}%` }}
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
