import { useEffect } from 'react';

import { Container } from '../components/layout/Container';
import { Footer } from '../components/layout/Footer';
import { Navbar } from '../components/layout/Navbar';
import { Button } from '../components/ui/Button';
import { GlassCard } from '../components/ui/GlassCard';
import { GradientText } from '../components/ui/GradientText';
import { Icon } from '../components/ui/Icon';
import { SectionHeading } from '../components/ui/SectionHeading';
import { brand, contact, cta } from '../content/site';
import { useReveal } from '../hooks/useReveal';

type ContactCardProps = {
  icon: string;
  iconTone: 'cyan' | 'emerald' | 'violet';
  label: string;
  title: string;
  hint: string;
  href: string;
  external?: boolean;
  actionLabel: string;
  actionIcon: string;
  ltr?: boolean;
};

const toneStyles = {
  cyan: {
    icon: 'border-modira-cyan/25 bg-modira-cyan/10 text-modira-cyan',
    glow: 'from-modira-cyan/20 via-transparent to-transparent',
    hover: 'hover:border-modira-cyan/35 hover:shadow-[0_24px_60px_-28px_color-mix(in_srgb,var(--modira-cyan)_45%,transparent)]',
  },
  emerald: {
    icon: 'border-modira-teal/25 bg-modira-teal/10 text-modira-teal',
    glow: 'from-modira-teal/20 via-transparent to-transparent',
    hover: 'hover:border-modira-teal/35 hover:shadow-[0_24px_60px_-28px_color-mix(in_srgb,var(--modira-teal)_45%,transparent)]',
  },
  violet: {
    icon: 'border-border-strong bg-surface-sunken text-fg',
    glow: 'from-modira-navy/20 via-transparent to-transparent',
    hover: 'hover:border-modira-teal/35 hover:shadow-[0_24px_60px_-28px_color-mix(in_srgb,var(--modira-teal)_45%,transparent)]',
  },
} as const;

function ContactCard({
  icon,
  iconTone,
  label,
  title,
  hint,
  href,
  external = false,
  actionLabel,
  actionIcon,
  ltr = false,
}: ContactCardProps) {
  const tone = toneStyles[iconTone];

  return (
    <a
      href={href}
      target={external ? '_blank' : undefined}
      rel={external ? 'noopener noreferrer' : undefined}
      className={`group relative block overflow-hidden rounded-3xl border border-border bg-surface-sunken p-6 transition-all duration-300 hover:-translate-y-1 ${tone.hover}`}
    >
      <div
        aria-hidden
        className={`pointer-events-none absolute inset-x-0 top-0 h-24 bg-gradient-to-b ${tone.glow}`}
      />
      <div className="relative flex items-start gap-4">
        <span
          className={`grid size-12 shrink-0 place-items-center rounded-2xl border ${tone.icon}`}
        >
          <Icon name={icon} size={22} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium text-subtle">{label}</p>
          <p className={`mt-1 text-lg font-bold text-fg ${ltr ? 'ltr' : ''}`}>{title}</p>
          <p className="mt-2 text-sm leading-relaxed text-muted">{hint}</p>
          <span className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-modira-cyan transition-colors group-hover:text-modira-cyan">
            {actionLabel}
            <Icon
              name={actionIcon}
              size={15}
              className="transition-transform group-hover:-translate-x-0.5"
            />
          </span>
        </div>
      </div>
    </a>
  );
}

export function ContactPage() {
  const { ref, isVisible } = useReveal<HTMLDivElement>();

  useEffect(() => {
    document.title = `تماس با ما | ${brand.nameFa}`;
    return () => {
      document.title = `مدیرا | ادمین هوشمند فروش اجتماعی`;
    };
  }, []);

  return (
    <>
      <Navbar />
      <main className="relative overflow-hidden pb-20 pt-28 sm:pt-36">
        <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
          <div className="absolute -top-24 start-1/2 size-[640px] -translate-x-1/2 rounded-full bg-modira-cyan/12 blur-[130px]" />
          <div className="absolute -end-24 top-40 size-[420px] rounded-full bg-modira-teal/8 blur-[120px]" />
          <div className="absolute -start-24 top-72 size-[380px] rounded-full bg-modira-teal/10 blur-[120px]" />
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-modira-cyan/30 to-transparent" />
        </div>

        <Container>
          <div
            ref={ref}
            className={`reveal mx-auto max-w-3xl text-center ${isVisible ? 'is-visible' : ''}`}
          >
            <SectionHeading
              eyebrow={contact.eyebrow}
              title={
                <>
                  با تیم <GradientText>{brand.nameFa}</GradientText> در ارتباط باشید
                </>
              }
              subtitle={contact.subtitle}
              align="center"
            />
          </div>

          <div className="mt-14 grid gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-stretch">
            <div className="flex flex-col gap-4">
              <ContactCard
                icon="Phone"
                iconTone="cyan"
                label={contact.phone.label}
                title={contact.phone.display}
                hint={contact.phone.hint}
                href={contact.phone.tel}
                actionLabel="تماس بگیرید"
                actionIcon="ArrowLeft"
                ltr
              />
              <ContactCard
                icon="MessageCircle"
                iconTone="emerald"
                label="واتساپ"
                title={contact.phone.display}
                hint="پیام سریع برای مشاوره، دمو یا پشتیبانی فنی"
                href={contact.phone.whatsapp}
                external
                actionLabel="ارسال پیام در واتساپ"
                actionIcon="ArrowLeft"
                ltr
              />
              <ContactCard
                icon="Linkedin"
                iconTone="violet"
                label={contact.linkedin.label}
                title={contact.linkedin.name}
                hint={contact.linkedin.hint}
                href={contact.linkedin.href}
                external
                actionLabel="مشاهده پروفایل لینکدین"
                actionIcon="ArrowLeft"
              />

              <GlassCard className="mt-2 flex flex-wrap items-center justify-between gap-4 p-5">
                <div className="flex items-center gap-3">
                  <span className="grid size-10 place-items-center rounded-2xl border border-border bg-surface-sunken text-fg/80">
                    <Icon name="Clock3" size={18} />
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-fg">{contact.hours}</p>
                    <p className="text-xs text-subtle">{contact.responseNote}</p>
                  </div>
                </div>
                <Button href={cta.primary.href} variant="primary" className="shrink-0 px-5 py-2.5">
                  <Icon name="Send" size={16} />
                  {cta.primary.label}
                </Button>
              </GlassCard>
            </div>

            <GlassCard strong className="overflow-hidden p-0">
              <div className="border-b border-border p-6">
                <div className="flex items-start gap-3">
                  <span className="grid size-11 shrink-0 place-items-center rounded-2xl border border-modira-cyan/25 bg-modira-cyan/10 text-modira-cyan">
                    <Icon name="MapPin" size={20} />
                  </span>
                  <div>
                    <p className="text-xs font-medium text-subtle">{contact.location.label}</p>
                    <h3 className="mt-1 text-xl font-bold text-fg">{contact.location.address}</h3>
                    <p className="mt-2 text-sm text-muted">{contact.location.hint}</p>
                    <a
                      href={contact.location.mapLink}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-modira-cyan transition-colors hover:text-modira-cyan"
                    >
                      مشاهده در نقشه
                      <Icon name="ExternalLink" size={14} />
                    </a>
                  </div>
                </div>
              </div>
              <div className="relative aspect-[4/3] min-h-[300px] w-full bg-surface sm:aspect-auto sm:min-h-[420px]">
                <iframe
                  title={`موقعیت ${brand.nameFa} روی نقشه`}
                  src={contact.location.mapEmbed}
                  className="absolute inset-0 h-full w-full border-0"
                  loading="lazy"
                  referrerPolicy="no-referrer-when-downgrade"
                />
                <div
                  aria-hidden
                  className="pointer-events-none absolute inset-x-0 top-0 h-10 bg-gradient-to-b from-modira-navy/70 to-transparent"
                />
              </div>
            </GlassCard>
          </div>

          <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button href="/" variant="secondary">
              <Icon name="Home" size={16} />
              بازگشت به صفحهٔ اصلی
            </Button>
            <Button href={cta.consult.href} variant="ghost">
              {cta.consult.label}
              <Icon name="ArrowLeft" size={16} />
            </Button>
          </div>
        </Container>
      </main>
      <Footer />
    </>
  );
}
