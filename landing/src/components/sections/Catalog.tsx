import { catalog } from '../../content/site';
import { Section } from '../layout/Section';
import { GlassCard } from '../ui/GlassCard';
import { Icon } from '../ui/Icon';
import { SectionHeading } from '../ui/SectionHeading';

export function Catalog() {
  return (
    <Section>
      <div className="grid items-center gap-10 lg:grid-cols-2">
        <div>
          <SectionHeading align="start" title={catalog.title} subtitle={catalog.subtitle} />
          <GlassCard strong className="mt-6 flex items-start gap-3 p-5">
            <span className="grid size-10 shrink-0 place-items-center rounded-2xl border border-modira-teal/25 bg-modira-teal/10 text-modira-teal">
              <Icon name="ShieldCheck" size={20} />
            </span>
            <p className="text-sm leading-relaxed text-fg">{catalog.emphasis}</p>
          </GlassCard>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {catalog.items.map((item) => (
            <GlassCard key={item.label} hover className="flex flex-col items-center gap-2 p-4 text-center">
              <span className="grid size-10 place-items-center rounded-xl border border-modira-cyan/20 bg-modira-cyan/10 text-modira-cyan">
                <Icon name={item.icon} size={18} />
              </span>
              <span className="text-xs font-medium text-fg">{item.label}</span>
            </GlassCard>
          ))}
        </div>
      </div>
    </Section>
  );
}
