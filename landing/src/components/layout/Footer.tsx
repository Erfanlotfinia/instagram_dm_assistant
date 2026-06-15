import { brand, channels, cta, footer } from '../../content/site';
import { Button } from '../ui/Button';
import { ChannelBadge } from '../mockups/ChannelBadge';
import { Icon } from '../ui/Icon';
import { Container } from './Container';

export function Footer() {
  return (
    <footer className="relative overflow-hidden border-t border-mist-200/10 pt-16 pb-10">
      {/* Top accent line + ambient glow */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan-400/40 to-transparent" />
        <div className="absolute -bottom-40 start-1/2 size-[520px] -translate-x-1/2 rounded-full bg-cyan-500/10 blur-[130px]" />
      </div>

      <Container>
        <div className="grid gap-12 lg:grid-cols-[1.5fr_1fr_1fr_1.1fr]">
          {/* Brand */}
          <div className="max-w-sm">
            <div className="flex items-center gap-2.5">
              <span className="grid size-10 place-items-center rounded-xl accent-gradient text-ink-950">
                <Icon name="Sparkles" size={20} />
              </span>
              <div className="leading-tight">
                <span className="ltr block text-lg font-extrabold text-mist-50">{footer.brand}</span>
                <span className="ltr block text-[11px] text-mist-500">{footer.tagline}</span>
              </div>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-mist-400">
              {brand.sloganFa}؛ یک سیستم‌عامل عملیاتی برای مدیریت پیام، فروش و پشتیبانی در همهٔ کانال‌ها.
            </p>
            <p className="mt-5 inline-flex items-center gap-1.5 rounded-full border border-cyan-400/20 bg-cyan-500/5 px-3 py-1 text-xs text-cyan-300">
              <Icon name="BadgeCheck" size={13} />
              {footer.note}
            </p>
          </div>

          {/* Link groups */}
          {footer.linkGroups.map((group) => (
            <div key={group.title}>
              <h3 className="text-sm font-bold text-mist-100">{group.title}</h3>
              <ul className="mt-4 space-y-3">
                {group.links.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      className="group inline-flex items-center gap-1.5 text-sm text-mist-400 transition-colors hover:text-cyan-300"
                    >
                      <Icon
                        name="ChevronLeft"
                        size={13}
                        className="text-mist-500 transition-all group-hover:-translate-x-0.5 group-hover:text-cyan-400"
                      />
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}

          {/* Channels + CTA */}
          <div>
            <h3 className="text-sm font-bold text-mist-100">کانال‌ها</h3>
            <div className="mt-4 flex flex-wrap gap-2">
              {channels.items.map((channel) => (
                <ChannelBadge key={channel.name} icon={channel.icon} name={channel.nameFa} />
              ))}
            </div>
            <Button href={cta.primary.href} variant="primary" className="mt-6 w-full">
              <Icon name="Send" size={16} />
              {cta.primary.label}
            </Button>
          </div>
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-3 border-t border-mist-200/10 pt-6 text-xs text-mist-500 sm:flex-row">
          <span className="ltr">© {new Date().getFullYear()} {footer.brand} — All rights reserved</span>
          <span>ساخته‌شده برای فروش اجتماعی واقعی</span>
        </div>
      </Container>
    </footer>
  );
}
