import { solution } from '../../content/site';
import { Section } from '../layout/Section';
import { FlowDiagram } from '../mockups/FlowDiagram';
import { GlassCard } from '../ui/GlassCard';
import { SectionHeading } from '../ui/SectionHeading';

export function Solution() {
  return (
    <Section>
      <SectionHeading title={solution.title} subtitle={solution.subtitle} />
      <GlassCard strong className="mt-12 p-5 sm:p-8">
        <FlowDiagram steps={solution.flow} />
      </GlassCard>
    </Section>
  );
}
