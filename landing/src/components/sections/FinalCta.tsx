import { cta, finalCta } from '../../content/site';
import { Container } from '../layout/Container';
import { Button } from '../ui/Button';
import { GradientText } from '../ui/GradientText';
import { Icon } from '../ui/Icon';

export function FinalCta() {
  return (
    <section id={finalCta.id} className="relative overflow-hidden py-24 sm:py-32">
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute start-1/2 top-1/2 size-[560px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-cyan-500/15 blur-[130px]" />
      </div>
      <Container>
        <div className="glass-strong relative mx-auto max-w-3xl overflow-hidden rounded-3xl p-8 text-center sm:p-12">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan-400/40 to-transparent" />
          <span className="grid size-14 mx-auto place-items-center rounded-2xl accent-gradient text-ink-950">
            <Icon name="Rocket" size={26} />
          </span>
          <h2 className="mt-6 text-2xl font-extrabold leading-tight text-mist-50 sm:text-4xl">
            ادمین شبکه‌های اجتماعی خود را <GradientText>هوشمند</GradientText> کنید
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-mist-300">
            {finalCta.text}
          </p>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <Button href={cta.primary.href} variant="primary">
              <Icon name="Send" size={16} />
              {cta.primary.label}
            </Button>
            <Button href={cta.consult.href} variant="secondary">
              {cta.consult.label}
              <Icon name="ArrowLeft" size={16} />
            </Button>
          </div>
        </div>
      </Container>
    </section>
  );
}
