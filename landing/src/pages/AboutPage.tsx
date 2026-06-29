import { useEffect, type ReactNode } from 'react';

import { Container } from '../components/layout/Container';
import { Footer } from '../components/layout/Footer';
import { Navbar } from '../components/layout/Navbar';
import { Button } from '../components/ui/Button';
import { GlassCard } from '../components/ui/GlassCard';
import { GradientText } from '../components/ui/GradientText';
import { Icon } from '../components/ui/Icon';
import { SectionHeading } from '../components/ui/SectionHeading';
import { about, brand } from '../content/site';
import { useReveal } from '../hooks/useReveal';

function PageSection({
  children,
  className = '',
  narrow = false,
}: {
  children: ReactNode;
  className?: string;
  narrow?: boolean;
}) {
  const { ref, isVisible } = useReveal<HTMLDivElement>();
  return (
    <section className={`py-14 sm:py-20 ${className}`}>
      <div ref={ref} className={`reveal ${isVisible ? 'is-visible' : ''}`}>
        <div className={narrow ? 'mx-auto max-w-3xl' : ''}>{children}</div>
      </div>
    </section>
  );
}

function BulletList({ items }: { items: readonly string[] }) {
  return (
    <ul className="grid gap-3 sm:grid-cols-2">
      {items.map((item) => (
        <li
          key={item}
          className="flex items-start gap-2.5 rounded-2xl border border-border bg-surface-sunken px-4 py-3 text-sm leading-relaxed text-fg"
        >
          <Icon name="Check" size={16} className="mt-0.5 shrink-0 text-modira-teal" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export function AboutPage() {
  useEffect(() => {
    document.title = about.meta.title;
    const meta = document.querySelector('meta[name="description"]');
    if (meta) meta.setAttribute('content', about.meta.description);
    return () => {
      document.title = `مدیرا | ادمین هوشمند فروش اجتماعی`;
    };
  }, []);

  return (
    <>
      <Navbar />
      <main className="relative overflow-hidden pb-16 pt-28 sm:pt-36">
        <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
          <div className="absolute -top-24 start-1/2 size-[700px] -translate-x-1/2 rounded-full bg-modira-cyan/10 blur-[140px]" />
          <div className="absolute top-80 -end-32 size-[460px] rounded-full bg-modira-teal/8 blur-[120px]" />
          <div className="absolute top-[520px] -start-32 size-[400px] rounded-full bg-modira-teal/8 blur-[120px]" />
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-modira-cyan/30 to-transparent" />
        </div>

        <Container>
          {/* Hero */}
          <div className="mx-auto max-w-4xl text-center">
            <SectionHeading
              eyebrow={about.eyebrow}
              title={
                <>
                  درباره <GradientText>{brand.name}</GradientText>؛ سیستم‌عامل هوشمند مدیریت شبکه‌های
                  اجتماعی
                </>
              }
              subtitle={about.subtitle}
              align="center"
            />
            <GlassCard className="mx-auto mt-10 max-w-3xl p-6 text-sm leading-relaxed text-fg/80 sm:p-8 sm:text-base">
              {about.summary}
            </GlassCard>
          </div>

          {/* Who we are */}
          <PageSection>
            <SectionHeading title={about.whoWeAre.title} align="start" />
            <GlassCard strong className="mt-8 p-6 sm:p-8">
              <p className="text-lg font-bold leading-relaxed text-modira-cyan">{about.whoWeAre.lead}</p>
              <div className="mt-6 space-y-4 text-sm leading-relaxed text-fg/80 sm:text-base">
                {about.whoWeAre.paragraphs.map((p) => (
                  <p key={p}>{p}</p>
                ))}
              </div>
            </GlassCard>
          </PageSection>

          {/* What we do */}
          <PageSection>
            <SectionHeading title={about.whatWeDo.title} subtitle={about.whatWeDo.intro} align="start" />
            <div className="mt-8 grid gap-3 sm:grid-cols-2">
              {about.whatWeDo.items.map((item) => (
                <GlassCard key={item.text} hover className="flex items-start gap-3 p-5">
                  <span className="grid size-10 shrink-0 place-items-center rounded-2xl border border-modira-cyan/25 bg-modira-cyan/10 text-modira-cyan">
                    <Icon name={item.icon} size={18} />
                  </span>
                  <p className="pt-1.5 text-sm leading-relaxed text-fg">{item.text}</p>
                </GlassCard>
              ))}
            </div>
            <p className="mt-8 rounded-2xl border border-modira-teal/20 bg-modira-teal/5 px-5 py-4 text-sm font-medium leading-relaxed text-modira-teal sm:text-base">
              {about.whatWeDo.emphasis}
            </p>
          </PageSection>

          {/* Why built */}
          <PageSection>
            <SectionHeading title={about.whyBuilt.title} subtitle={about.whyBuilt.intro} align="start" />
            <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {about.whyBuilt.problems.map((item) => (
                <GlassCard key={item.text} className="p-4">
                  <span className="grid size-9 place-items-center rounded-xl border border-border bg-surface-sunken text-muted">
                    <Icon name={item.icon} size={16} />
                  </span>
                  <p className="mt-3 text-sm leading-relaxed text-fg/80">{item.text}</p>
                </GlassCard>
              ))}
            </div>
            <p className="mt-8 text-center text-base font-semibold text-fg">{about.whyBuilt.closing}</p>
          </PageSection>

          {/* Mission & Vision */}
          <PageSection>
            <div className="grid gap-6 lg:grid-cols-2">
              <GlassCard strong hover className="p-6 sm:p-8">
                <span className="inline-flex items-center gap-2 rounded-full border border-modira-cyan/25 bg-modira-cyan/5 px-3 py-1 text-xs font-medium text-modira-cyan">
                  <Icon name="Target" size={13} />
                  {about.mission.title}
                </span>
                <p className="mt-5 text-base font-semibold leading-relaxed text-fg">{about.mission.text}</p>
                <p className="mt-4 text-sm leading-relaxed text-muted">{about.mission.note}</p>
              </GlassCard>
              <GlassCard strong hover className="p-6 sm:p-8">
                <span className="inline-flex items-center gap-2 rounded-full border border-modira-teal/25 bg-modira-teal/5 px-3 py-1 text-xs font-medium text-modira-teal">
                  <Icon name="Telescope" size={13} />
                  {about.vision.title}
                </span>
                <p className="mt-5 text-base font-semibold leading-relaxed text-fg">{about.vision.text}</p>
                <p className="mt-4 text-sm leading-relaxed text-muted">{about.vision.note}</p>
              </GlassCard>
            </div>
          </PageSection>

          {/* Values */}
          <PageSection>
            <SectionHeading title={about.values.title} align="start" />
            <div className="mt-8 grid gap-4 lg:grid-cols-2">
              {about.values.items.map((value) => (
                <GlassCard key={value.title} hover className="p-6">
                  <div className="flex items-start gap-4">
                    <span className="ltr text-xs font-bold text-subtle">{value.order}</span>
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <span className="grid size-10 place-items-center rounded-2xl border border-border-strong bg-surface text-fg">
                          <Icon name={value.icon} size={18} />
                        </span>
                        <h3 className="text-lg font-bold text-fg">{value.title}</h3>
                      </div>
                      <p className="mt-3 text-sm leading-relaxed text-muted">{value.text}</p>
                    </div>
                  </div>
                </GlassCard>
              ))}
            </div>
          </PageSection>

          {/* Comparison */}
          <PageSection>
            <SectionHeading title={about.comparison.title} subtitle={about.comparison.intro} align="start" />
            <GlassCard strong className="mt-8 overflow-hidden p-0">
              <div className="hidden overflow-x-auto sm:block">
                <table className="w-full min-w-[560px] text-sm">
                  <thead>
                    <tr className="border-b border-border bg-surface-sunken">
                      {about.comparison.columns.map((col, i) => (
                        <th
                          key={col}
                          className={`px-5 py-4 text-start font-bold ${
                            i === 2 ? 'text-modira-cyan' : 'text-fg'
                          }`}
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {about.comparison.rows.map((row) => (
                      <tr
                        key={row.feature}
                        className="border-b border-border transition-colors hover:bg-surface-sunken"
                      >
                        <td className="px-5 py-3.5 font-medium text-fg">{row.feature}</td>
                        <td className="px-5 py-3.5 text-subtle">{row.chatbot}</td>
                        <td
                          className={`px-5 py-3.5 ${
                            row.modiraStrong ? 'font-semibold text-modira-teal' : 'text-fg/80'
                          }`}
                        >
                          {row.modira}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex flex-col gap-3 p-4 sm:hidden">
                {about.comparison.rows.map((row) => (
                  <div key={row.feature} className="rounded-2xl border border-border bg-surface-sunken p-4">
                    <p className="font-semibold text-fg">{row.feature}</p>
                    <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
                      <div>
                        <p className="text-subtle">چت‌بات معمولی</p>
                        <p className="mt-1 text-muted">{row.chatbot}</p>
                      </div>
                      <div>
                        <p className="text-modira-cyan">مدیرا</p>
                        <p
                          className={`mt-1 ${row.modiraStrong ? 'font-semibold text-modira-teal' : 'text-fg/80'}`}
                        >
                          {row.modira}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </GlassCard>
          </PageSection>

          {/* Technology */}
          <PageSection>
            <SectionHeading title={about.technology.title} subtitle={about.technology.intro} align="start" />
            <div className="mt-8 grid gap-4 lg:grid-cols-3">
              {about.technology.layers.map((layer) => (
                <GlassCard key={layer.title} hover className="relative overflow-hidden p-6">
                  <div
                    aria-hidden
                    className="pointer-events-none absolute -end-4 -top-4 text-7xl font-extrabold text-white/[0.03]"
                  >
                    {layer.order}
                  </div>
                  <span className="grid size-11 place-items-center rounded-2xl border border-modira-cyan/25 bg-modira-cyan/10 text-modira-cyan">
                    <Icon name={layer.icon} size={20} />
                  </span>
                  <h3 className="mt-4 text-lg font-bold text-fg">{layer.title}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-muted">{layer.text}</p>
                </GlassCard>
              ))}
            </div>
            <p className="mt-8 text-center text-sm leading-relaxed text-muted sm:text-base">
              {about.technology.closing}
            </p>
          </PageSection>

          {/* Audience */}
          <PageSection>
            <SectionHeading title={about.audience.title} subtitle={about.audience.intro} align="start" />
            <div className="mt-8 flex flex-wrap gap-2.5">
              {about.audience.segments.map((segment) => (
                <span
                  key={segment}
                  className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-sunken px-4 py-2 text-sm text-fg"
                >
                  <span className="size-1.5 rounded-full accent-gradient" />
                  {segment}
                </span>
              ))}
            </div>
            <p className="mt-8 text-sm leading-relaxed text-muted sm:text-base">{about.audience.categories}</p>
          </PageSection>

          {/* Why need + Commitment */}
          <PageSection>
            <div className="grid gap-8 lg:grid-cols-2">
              <div>
                <SectionHeading title={about.whyNeed.title} subtitle={about.whyNeed.lead} align="start" />
                <div className="mt-6">
                  <BulletList items={about.whyNeed.benefits} />
                </div>
              </div>
              <div>
                <SectionHeading
                  title={about.commitment.title}
                  subtitle={about.commitment.intro}
                  align="start"
                />
                <p className="mt-4 text-sm leading-relaxed text-muted">{about.commitment.note}</p>
                <div className="mt-6">
                  <BulletList items={about.commitment.focus} />
                </div>
              </div>
            </div>
          </PageSection>

          {/* Future */}
          <PageSection narrow>
            <GlassCard strong className="p-6 text-center sm:p-10">
              <span className="grid size-14 mx-auto place-items-center rounded-2xl accent-gradient text-modira-navy-deep">
                <Icon name="Rocket" size={26} />
              </span>
              <h2 className="mt-6 text-2xl font-extrabold text-fg sm:text-3xl">{about.future.title}</h2>
              <div className="mx-auto mt-5 max-w-2xl space-y-4 text-sm leading-relaxed text-fg/80 sm:text-base">
                {about.future.paragraphs.map((p) => (
                  <p key={p}>{p}</p>
                ))}
              </div>
            </GlassCard>
          </PageSection>

          {/* CTA */}
          <PageSection narrow>
            <GlassCard strong className="relative overflow-hidden p-8 text-center sm:p-12">
              <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-modira-cyan/40 to-transparent" />
              <h2 className="text-2xl font-extrabold leading-tight text-fg sm:text-3xl">
                {about.cta.title}
              </h2>
              <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-fg/80">{about.cta.text}</p>
              <p className="mt-4 text-sm font-semibold text-modira-cyan">{about.cta.tagline}</p>
              <div className="mt-8 flex flex-col flex-wrap justify-center gap-3 sm:flex-row">
                {about.cta.buttons.map((btn) => (
                  <Button key={btn.label} href={btn.href} variant={btn.variant} className="px-5 py-2.5">
                    <Icon name={btn.icon} size={16} />
                    {btn.label}
                  </Button>
                ))}
              </div>
            </GlassCard>
          </PageSection>
        </Container>
      </main>
      <Footer />
    </>
  );
}
