import { problem } from '../../content/site';
import { Section } from '../layout/Section';
import { GlassCard } from '../ui/GlassCard';
import { Icon } from '../ui/Icon';
import { SectionHeading } from '../ui/SectionHeading';

export function Problem() {
  return (
    <Section id={problem.id}>
      <SectionHeading title={problem.title} subtitle={problem.subtitle} />
      <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {problem.items.map((item) => (
          <GlassCard key={item.title} hover className="p-6">
            <span className="grid size-11 place-items-center rounded-2xl border border-rose-400/20 bg-rose-500/10 text-rose-300">
              <Icon name={item.icon} size={20} />
            </span>
            <h3 className="mt-4 text-base font-bold text-mist-50">{item.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-mist-400">{item.text}</p>
          </GlassCard>
        ))}
      </div>
    </Section>
  );
}
