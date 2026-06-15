import { philosophy } from '../../content/site';
import { Section } from '../layout/Section';
import { Badge } from '../ui/Badge';
import { GlassCard } from '../ui/GlassCard';
import { Icon } from '../ui/Icon';
import { SectionHeading } from '../ui/SectionHeading';

export function Philosophy() {
  return (
    <Section>
      <SectionHeading title={philosophy.title} subtitle={philosophy.subtitle} />
      <div className="mt-12 grid gap-4 md:grid-cols-3">
        {philosophy.pillars.map((pillar, i) => (
          <GlassCard
            key={pillar.tag}
            strong
            hover
            className="relative overflow-hidden p-6"
          >
            <span className="ltr absolute -top-3 left-4 text-6xl font-black text-white/5">
              {pillar.order}
            </span>
            <div className="relative">
              <span className="grid size-12 place-items-center rounded-2xl accent-gradient text-ink-950">
                <Icon name={pillar.icon} size={22} />
              </span>
              <div className="mt-4">
                <Badge tone={i === 2 ? 'emerald' : 'cyan'}>{pillar.tag}</Badge>
              </div>
              <h3 className="mt-3 text-lg font-bold text-mist-50">{pillar.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-mist-400">{pillar.text}</p>
            </div>
          </GlassCard>
        ))}
      </div>
    </Section>
  );
}
