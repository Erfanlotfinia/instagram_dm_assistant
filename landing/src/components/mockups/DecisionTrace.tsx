import { Icon } from '../ui/Icon';

type TraceStep = {
  label: string;
  kind: 'automation' | 'llm' | 'human' | 'data';
};

const kindStyle: Record<TraceStep['kind'], { dot: string; tag: string; tagText: string }> = {
  automation: { dot: 'bg-modira-cyan', tag: 'bg-modira-cyan/10 text-modira-cyan', tagText: 'Automation' },
  data: { dot: 'bg-modira-teal', tag: 'bg-modira-teal/10 text-modira-teal', tagText: 'Data' },
  llm: { dot: 'bg-modira-teal-dark', tag: 'bg-modira-teal/10 text-modira-teal', tagText: 'LLM' },
  human: { dot: 'bg-fg', tag: 'border border-border-strong bg-surface-sunken text-fg', tagText: 'Human' },
};

const defaultSteps: TraceStep[] = [
  { label: 'تشخیص نیت: قیمت محصول', kind: 'automation' },
  { label: 'تطبیق پست با کاتالوگ', kind: 'data' },
  { label: 'بررسی موجودی و قیمت', kind: 'data' },
  { label: 'رفع ابهام رنگ با زبان طبیعی', kind: 'llm' },
];

export function DecisionTrace({ steps = defaultSteps, title = 'ردگیری تصمیم' }: {
  steps?: TraceStep[];
  title?: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface/50 p-3">
      <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-fg">
        <Icon name="GitBranch" size={14} className="text-modira-cyan" />
        {title}
      </div>
      <ol className="relative space-y-2.5 ps-4">
        <span className="absolute inset-y-1 start-[5px] w-px bg-border" />
        {steps.map((step) => {
          const s = kindStyle[step.kind];
          return (
            <li key={step.label} className="relative flex items-center justify-between gap-2">
              <span className={`absolute -start-4 top-1.5 size-2.5 rounded-full ${s.dot}`} />
              <span className="text-xs text-fg">{step.label}</span>
              <span className={`ltr shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-medium ${s.tag}`}>
                {s.tagText}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
