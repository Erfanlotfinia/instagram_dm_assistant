import { security } from '../../content/site';
import { Section } from '../layout/Section';
import { GlassCard } from '../ui/GlassCard';
import { Icon } from '../ui/Icon';
import { SectionHeading } from '../ui/SectionHeading';

export function Security() {
  return (
    <Section id={security.id}>
      <SectionHeading title={security.title} subtitle={security.subtitle} />
      <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {security.items.map((item) => (
          <GlassCard key={item.text} hover className="flex items-start gap-3 p-5">
            <span className="grid size-10 shrink-0 place-items-center rounded-2xl border border-modira-teal/25 bg-modira-teal/10 text-modira-teal">
              <Icon name={item.icon} size={18} />
            </span>
            <p className="pt-1.5 text-sm leading-relaxed text-fg">{item.text}</p>
          </GlassCard>
        ))}
      </div>
    </Section>
  );
}
