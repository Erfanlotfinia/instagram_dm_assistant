import { Icon } from '../ui/Icon';

type Step = { label: string; done: boolean; active?: boolean };

type OrderStatusCardProps = {
  orderId: string;
  steps?: Step[];
};

const defaultSteps: Step[] = [
  { label: 'ثبت', done: true },
  { label: 'پرداخت', done: true },
  { label: 'ارسال', done: false, active: true },
  { label: 'تحویل', done: false },
];

export function OrderStatusCard({ orderId, steps = defaultSteps }: OrderStatusCardProps) {
  return (
    <div className="rounded-2xl border border-border bg-surface-sunken p-3">
      <div className="mb-3 flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-xs font-semibold text-fg">
          <Icon name="Receipt" size={14} className="text-modira-cyan" />
          سفارش
        </span>
        <span className="ltr rounded-md bg-surface px-2 py-0.5 text-[11px] text-fg/80">
          {orderId}
        </span>
      </div>
      <div className="flex items-center">
        {steps.map((step, i) => (
          <div key={step.label} className="flex flex-1 items-center last:flex-none">
            <div className="flex flex-col items-center gap-1">
              <span
                className={`grid size-6 place-items-center rounded-full text-[10px] ${
                  step.done
                    ? 'accent-gradient text-modira-navy-deep'
                    : step.active
                      ? 'border border-modira-cyan/50 bg-modira-cyan/15 text-modira-cyan animate-pulse-dot'
                      : 'border border-border bg-surface-sunken text-subtle'
                }`}
              >
                {step.done ? <Icon name="Check" size={12} /> : i + 1}
              </span>
              <span className="text-[10px] text-muted">{step.label}</span>
            </div>
            {i < steps.length - 1 ? (
              <span
                className={`mx-1 h-px flex-1 ${
                  step.done ? 'bg-modira-cyan/40' : 'bg-border'
                }`}
              />
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}
