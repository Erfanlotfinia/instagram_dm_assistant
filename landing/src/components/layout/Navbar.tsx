import { useEffect, useState } from 'react';

import { brand, cta, nav } from '../../content/site';
import { Button } from '../ui/Button';
import { Icon } from '../ui/Icon';
import { Container } from './Container';

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [open]);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${
        scrolled ? 'py-2' : 'py-4'
      }`}
    >
      <Container>
        <nav
          aria-label="ناوبری اصلی"
          className={`flex items-center justify-between rounded-2xl px-4 py-2.5 transition-all duration-300 ${
            scrolled ? 'glass-strong' : ''
          }`}
        >
          <a href="#top" className="flex items-center gap-2" aria-label={`${brand.name} — خانه`}>
            <span className="grid size-9 place-items-center rounded-xl accent-gradient text-ink-950">
              <Icon name="Sparkles" size={18} />
            </span>
            <span className="ltr text-lg font-extrabold tracking-tight text-mist-50">
              {brand.name}
            </span>
          </a>

          <ul className="hidden items-center gap-1 lg:flex">
            {nav.links.map((link) => (
              <li key={link.href}>
                <a
                  href={link.href}
                  className="rounded-xl px-3 py-2 text-sm text-mist-300 transition-colors hover:text-mist-50"
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>

          <div className="hidden items-center gap-2 lg:flex">
            <Button href={cta.panel.href} variant="secondary" className="px-5 py-2.5">
              <Icon name="LogIn" size={16} />
              {cta.panel.label}
            </Button>
            <Button href={cta.primary.href} variant="primary" className="px-5 py-2.5">
              {cta.primary.label}
            </Button>
          </div>

          <button
            type="button"
            className="grid size-10 place-items-center rounded-xl text-mist-100 lg:hidden"
            aria-label={open ? 'بستن منو' : 'باز کردن منو'}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            <Icon name={open ? 'X' : 'Menu'} size={22} />
          </button>
        </nav>
      </Container>

      {/* Mobile drawer */}
      {open ? (
        <div className="lg:hidden">
          <Container>
            <div className="glass-strong mt-2 rounded-2xl p-4">
              <ul className="flex flex-col gap-1">
                {nav.links.map((link) => (
                  <li key={link.href}>
                    <a
                      href={link.href}
                      onClick={() => setOpen(false)}
                      className="block rounded-xl px-3 py-3 text-mist-200 transition-colors hover:bg-white/5 hover:text-mist-50"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
              <Button
                href={cta.panel.href}
                variant="secondary"
                className="mt-3 w-full"
                onClick={() => setOpen(false)}
              >
                <Icon name="LogIn" size={16} />
                {cta.panel.label}
              </Button>
              <Button
                href={cta.primary.href}
                variant="primary"
                className="mt-2 w-full"
                onClick={() => setOpen(false)}
              >
                {cta.primary.label}
              </Button>
            </div>
          </Container>
        </div>
      ) : null}
    </header>
  );
}
