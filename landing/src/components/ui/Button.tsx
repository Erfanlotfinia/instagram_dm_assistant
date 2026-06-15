import type { AnchorHTMLAttributes, ReactNode } from 'react';

type Variant = 'primary' | 'secondary' | 'ghost';

type ButtonProps = AnchorHTMLAttributes<HTMLAnchorElement> & {
  variant?: Variant;
  children: ReactNode;
};

const base =
  'inline-flex items-center justify-center gap-2 rounded-2xl px-6 py-3 text-sm font-semibold transition-all duration-300 focus-visible:outline-none';

const variants: Record<Variant, string> = {
  primary:
    'accent-gradient text-ink-950 shadow-[0_18px_45px_-15px_rgba(6,182,212,0.7)] hover:shadow-[0_22px_55px_-12px_rgba(16,185,129,0.7)] hover:-translate-y-0.5',
  secondary:
    'glass text-mist-50 hover:border-cyan-400/40 hover:-translate-y-0.5',
  ghost: 'text-mist-200 hover:text-mist-50',
};

export function Button({ variant = 'primary', children, className = '', ...props }: ButtonProps) {
  return (
    <a className={`${base} ${variants[variant]} ${className}`} {...props}>
      {children}
    </a>
  );
}
