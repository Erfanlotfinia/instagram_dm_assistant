import { pilot } from '../../content/site';
import { Section } from '../layout/Section';
import { GlassCard } from '../ui/GlassCard';
import { Icon } from '../ui/Icon';
import { SectionHeading } from '../ui/SectionHeading';

const persianNumber = (n: number) =>
  String(n).replace(/\d/g, (d) => '۰۱۲۳۴۵۶۷۸۹'[Number(d)]);

export function Pilot() {
  return (
    <Section id={pilot.id}>
      <SectionHeading title={pilot.title} subtitle={pilot.subtitle} />
      <ol className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {pilot.stages.map((stage, i) => {
          const highlight = i === 3 || i === 4; // Shadow + Copilot
          return (
            <li key={stage.title}>
              <GlassCard
                strong={highlight}
                hover
                className={`h-full p-5 ${highlight ? 'ring-glow' : ''}`}
              >
                <div className="flex items-center justify-between">
                  <span className="grid size-11 place-items-center rounded-2xl border border-modira-cyan/20 bg-modira-cyan/10 text-modira-cyan">
                    <Icon name={stage.icon} size={20} />
                  </span>
                  <span className="ltr text-2xl font-black text-white/10">
                    {persianNumber(i + 1)}
                  </span>
                </div>
                <h3 className="mt-4 text-base font-bold text-fg">{stage.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted">{stage.text}</p>
              </GlassCard>
            </li>
          );
        })}
      </ol>
    </Section>
  );
}
