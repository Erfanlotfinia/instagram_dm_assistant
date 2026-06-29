import { brand, channels, cta, footer } from '../../content/site';
import { Button } from '../ui/Button';
import { ChannelBadge } from '../mockups/ChannelBadge';
import { Icon } from '../ui/Icon';
import { Logo } from '../brand/Logo';
import { Container } from './Container';

export function Footer() {
  return (
    <footer className="relative overflow-hidden border-t border-border pt-16 pb-10">
      {/* Top accent line + ambient glow */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-modira-cyan/40 to-transparent" />
        <div className="absolute -bottom-40 start-1/2 size-[520px] -translate-x-1/2 rounded-full bg-modira-cyan/10 blur-[130px]" />
      </div>

      <Container>
        <div className="grid gap-12 lg:grid-cols-[1.5fr_1fr_1fr_1.1fr]">
          {/* Brand */}
          <div className="max-w-sm">
            <div className="flex items-center gap-2.5">
              <span className="grid size-10 place-items-center rounded-xl accent-gradient">
                <Logo variant="mark" reversed alt="" className="h-6 w-auto" />
              </span>
              <div className="leading-tight">
                <span className="ltr block text-lg font-extrabold text-fg">{footer.brand}</span>
                <span className="ltr block text-[11px] text-subtle">{footer.tagline}</span>
              </div>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-muted">
              {brand.sloganFa}؛ یک سیستم‌عامل عملیاتی برای مدیریت پیام، فروش و پشتیبانی در همهٔ کانال‌ها.
            </p>
            <p className="mt-5 inline-flex items-center gap-1.5 rounded-full border border-modira-cyan/20 bg-modira-cyan/5 px-3 py-1 text-xs text-modira-cyan">
              <Icon name="BadgeCheck" size={13} />
              {footer.note}
            </p>
          </div>

          {/* Link groups */}
          {footer.linkGroups.map((group) => (
            <div key={group.title}>
              <h3 className="text-sm font-bold text-fg">{group.title}</h3>
              <ul className="mt-4 space-y-3">
                {group.links.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      className="group inline-flex items-center gap-1.5 text-sm text-muted transition-colors hover:text-modira-cyan"
                    >
                      <Icon
                        name="ChevronLeft"
                        size={13}
                        className="text-subtle transition-all group-hover:-translate-x-0.5 group-hover:text-modira-cyan"
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
            <h3 className="text-sm font-bold text-fg">کانال‌ها</h3>
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

        <div className="mt-12 flex flex-col items-center justify-between gap-3 border-t border-border pt-6 text-xs text-subtle sm:flex-row">
          <span className="ltr">© {new Date().getFullYear()} {footer.brand} — All rights reserved</span>
          <span>ساخته‌شده برای فروش اجتماعی واقعی</span>
        </div>
      </Container>
    </footer>
  );
}
