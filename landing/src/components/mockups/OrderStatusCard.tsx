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
    <div className="rounded-2xl border border-mist-200/10 bg-white/5 p-3">
      <div className="mb-3 flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-xs font-semibold text-mist-200">
          <Icon name="Receipt" size={14} className="text-cyan-400" />
          سفارش
        </span>
        <span className="ltr rounded-md bg-ink-700/60 px-2 py-0.5 text-[11px] text-mist-300">
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
                    ? 'accent-gradient text-ink-950'
                    : step.active
                      ? 'border border-cyan-400/50 bg-cyan-500/15 text-cyan-300 animate-pulse-dot'
                      : 'border border-mist-200/15 bg-white/5 text-mist-500'
                }`}
              >
                {step.done ? <Icon name="Check" size={12} /> : i + 1}
              </span>
              <span className="text-[10px] text-mist-400">{step.label}</span>
            </div>
            {i < steps.length - 1 ? (
              <span
                className={`mx-1 h-px flex-1 ${
                  step.done ? 'bg-cyan-400/40' : 'bg-mist-200/10'
                }`}
              />
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}
