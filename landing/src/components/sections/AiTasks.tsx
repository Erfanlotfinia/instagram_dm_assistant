import { aiTasks } from '../../content/site';
import { Section } from '../layout/Section';
import { GlassCard } from '../ui/GlassCard';
import { Icon } from '../ui/Icon';
import { SectionHeading } from '../ui/SectionHeading';

export function AiTasks() {
  return (
    <Section>
      <SectionHeading title={aiTasks.title} subtitle={aiTasks.subtitle} />
      <div className="mt-12 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {aiTasks.items.map((item) => (
          <GlassCard key={item.label} hover className="flex items-center gap-3 p-4">
            <span className="grid size-10 shrink-0 place-items-center rounded-xl border border-cyan-400/20 bg-cyan-500/10 text-cyan-300">
              <Icon name={item.icon} size={18} />
            </span>
            <span className="text-sm font-medium text-mist-100">{item.label}</span>
          </GlassCard>
        ))}
      </div>
      <div className="mt-6 flex items-center justify-center">
        <p className="flex items-center gap-2 rounded-2xl border border-amber-400/25 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          <Icon name="ShieldCheck" size={16} />
          {aiTasks.note}
        </p>
      </div>
    </Section>
  );
}
