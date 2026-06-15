import { scenarios } from '../../content/site';
import { Section } from '../layout/Section';
import { ChatBubble } from '../mockups/ChatBubble';
import { Badge } from '../ui/Badge';
import { GlassCard } from '../ui/GlassCard';
import { Icon } from '../ui/Icon';
import { SectionHeading } from '../ui/SectionHeading';

export function Scenarios() {
  return (
    <Section id={scenarios.id}>
      <SectionHeading title={scenarios.title} subtitle={scenarios.subtitle} />
      <div className="mt-12 grid gap-4 lg:grid-cols-2">
        {scenarios.items.map((item) => (
          <GlassCard key={item.title} strong hover className="flex flex-col p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <span className="grid size-10 place-items-center rounded-2xl border border-cyan-400/20 bg-cyan-500/10 text-cyan-300">
                  <Icon name={item.icon} size={18} />
                </span>
                <h3 className="text-sm font-bold text-mist-50">{item.title}</h3>
              </div>
              <Badge tone="cyan">{item.tag}</Badge>
            </div>
            <div className="flex flex-1 flex-col gap-3 rounded-2xl bg-ink-900/40 p-4">
              {item.bubbles.map((bubble, i) => (
                <ChatBubble key={i} {...bubble} />
              ))}
            </div>
          </GlassCard>
        ))}
      </div>
    </Section>
  );
}
