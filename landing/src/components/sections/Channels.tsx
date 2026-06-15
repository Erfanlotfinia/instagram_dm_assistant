import { channels } from '../../content/site';
import { Section } from '../layout/Section';
import { GlassCard } from '../ui/GlassCard';
import { Icon } from '../ui/Icon';
import { SectionHeading } from '../ui/SectionHeading';

export function Channels() {
  return (
    <Section id={channels.id}>
      <SectionHeading title={channels.title} subtitle={channels.subtitle} />
      <div className="mt-12 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {channels.items.map((channel, i) => {
          const future = i === channels.items.length - 1;
          return (
            <GlassCard
              key={channel.name}
              hover
              className={`flex flex-col items-center gap-3 p-5 text-center ${
                future ? 'border-dashed' : ''
              }`}
            >
              <span
                className={`grid size-12 place-items-center rounded-2xl ${
                  future
                    ? 'border border-dashed border-mist-200/25 text-mist-400'
                    : 'accent-gradient text-ink-950'
                }`}
              >
                <Icon name={channel.icon} size={22} />
              </span>
              <div>
                <p className="ltr text-sm font-bold text-mist-50">{channel.name}</p>
                <p className="mt-0.5 text-xs text-mist-400">{channel.nameFa}</p>
              </div>
            </GlassCard>
          );
        })}
      </div>
    </Section>
  );
}
