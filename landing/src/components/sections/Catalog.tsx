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
            <span className="grid size-10 shrink-0 place-items-center rounded-2xl border border-emerald-400/25 bg-emerald-500/10 text-emerald-300">
              <Icon name="ShieldCheck" size={20} />
            </span>
            <p className="text-sm leading-relaxed text-mist-100">{catalog.emphasis}</p>
          </GlassCard>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {catalog.items.map((item) => (
            <GlassCard key={item.label} hover className="flex flex-col items-center gap-2 p-4 text-center">
              <span className="grid size-10 place-items-center rounded-xl border border-cyan-400/20 bg-cyan-500/10 text-cyan-300">
                <Icon name={item.icon} size={18} />
              </span>
              <span className="text-xs font-medium text-mist-200">{item.label}</span>
            </GlassCard>
          ))}
        </div>
      </div>
    </Section>
  );
}
