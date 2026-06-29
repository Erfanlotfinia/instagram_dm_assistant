import { Icon } from '../ui/Icon';

type FlowStep = { icon: string; label: string };

export function FlowDiagram({ steps }: { steps: readonly FlowStep[] }) {
  return (
    <div className="flex flex-col items-stretch gap-3 lg:flex-row lg:items-stretch">
      {steps.map((step, i) => (
        <div key={step.label} className="flex flex-col items-center lg:flex-1 lg:flex-row">
          <div className="glass flex w-full items-center gap-3 rounded-2xl p-3 lg:flex-col lg:gap-2 lg:p-4 lg:text-center">
            <span className="grid size-10 shrink-0 place-items-center rounded-xl border border-modira-cyan/25 bg-modira-cyan/10 text-modira-cyan">
              <Icon name={step.icon} size={18} />
            </span>
            <span className="text-sm font-medium text-fg lg:text-[13px]">{step.label}</span>
          </div>
          {i < steps.length - 1 ? (
            <span className="my-1 text-modira-cyan/60 lg:mx-1 lg:my-0">
              {/* Down arrow on mobile, left arrow (RTL flow) on desktop */}
              <Icon name="ChevronDown" size={18} className="lg:hidden" />
              <Icon name="ChevronLeft" size={18} className="hidden lg:block" />
            </span>
          ) : null}
        </div>
      ))}
    </div>
  );
}
