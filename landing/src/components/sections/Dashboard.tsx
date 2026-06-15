import { dashboard } from '../../content/site';
import { Section } from '../layout/Section';
import { DashboardMockup } from '../mockups/DashboardMockup';
import { SectionHeading } from '../ui/SectionHeading';

export function Dashboard() {
  return (
    <Section>
      <SectionHeading title={dashboard.title} subtitle={dashboard.subtitle} />
      <div className="mt-12">
        <DashboardMockup />
      </div>
    </Section>
  );
}
