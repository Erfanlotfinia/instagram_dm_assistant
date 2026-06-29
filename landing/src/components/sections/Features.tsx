import { features } from '../../content/site';
import { Section } from '../layout/Section';
import { GlassCard } from '../ui/GlassCard';
import { Icon } from '../ui/Icon';
import { SectionHeading } from '../ui/SectionHeading';

export function Features() {
  return (
    <Section id={features.id}>
      <SectionHeading title={features.title} subtitle={features.subtitle} />
      <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {features.items.map((item) => (
          <GlassCard key={item.title} hover className="group p-5">
            <span className="grid size-11 place-items-center rounded-2xl border border-modira-cyan/20 bg-modira-cyan/10 text-modira-cyan transition-transform duration-300 group-hover:scale-110">
              <Icon name={item.icon} size={20} />
            </span>
            <h3 className="mt-4 text-base font-bold text-fg">{item.title}</h3>
            <p className="mt-1.5 text-sm leading-relaxed text-muted">{item.text}</p>
          </GlassCard>
        ))}
      </div>
    </Section>
  );
}
