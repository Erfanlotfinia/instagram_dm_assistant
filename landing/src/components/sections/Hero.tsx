import { cta, hero } from '../../content/site';
import { Container } from '../layout/Container';
import { CommandCenter } from '../mockups/CommandCenter';
import { Button } from '../ui/Button';
import { GradientText } from '../ui/GradientText';
import { Icon } from '../ui/Icon';

export function Hero() {
  return (
    <section id="top" className="relative overflow-hidden pb-16 pt-32 sm:pb-24 sm:pt-40">
      {/* Ambient gradient glows */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -top-40 start-1/2 size-[640px] -translate-x-1/2 rounded-full bg-modira-cyan/15 blur-[120px]" />
        <div className="absolute -right-32 top-40 size-[420px] rounded-full bg-modira-teal/10 blur-[120px]" />
        <div className="absolute -left-32 top-60 size-[420px] rounded-full bg-modira-teal-dark/20 blur-[120px]" />
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-modira-cyan/30 to-transparent" />
      </div>

      <Container>
        <div className="mx-auto flex max-w-3xl flex-col items-center text-center">
          <span className="ltr mb-6 inline-flex items-center gap-2 rounded-full border border-modira-cyan/25 bg-modira-cyan/5 px-4 py-1.5 text-xs font-medium text-modira-cyan">
            <Icon name="Sparkles" size={13} />
            {hero.eyebrow}
          </span>

          <h1 className="text-balance text-3xl font-extrabold leading-[1.25] text-fg sm:text-5xl sm:leading-[1.2]">
            مدیرا؛ <GradientText>ادمین هوشمند فروش اجتماعی</GradientText> شما
          </h1>

          <p className="mt-6 max-w-2xl text-base leading-relaxed text-fg/80 sm:text-lg">
            {hero.subheadline}
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button href={cta.primary.href} variant="primary">
              <Icon name="Send" size={16} />
              {cta.primary.label}
            </Button>
            <Button href={cta.secondary.href} variant="secondary">
              {cta.secondary.label}
              <Icon name="ArrowLeft" size={16} />
            </Button>
          </div>

          <ul className="mt-9 flex flex-wrap items-center justify-center gap-2">
            {hero.badges.map((badge) => (
              <li
                key={badge}
                className="ltr flex items-center gap-1.5 rounded-full border border-border bg-surface-sunken px-3 py-1.5 text-xs font-medium text-fg"
              >
                <span className="size-1.5 rounded-full accent-gradient" />
                {badge}
              </li>
            ))}
          </ul>
        </div>

        <div className="relative mt-14 animate-float-slow sm:mt-16">
          <CommandCenter />
        </div>
      </Container>
    </section>
  );
}
