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
    'accent-gradient text-modira-navy-deep shadow-[0_18px_45px_-15px_color-mix(in_srgb,var(--modira-cyan)_70%,transparent)] hover:shadow-[0_22px_55px_-12px_color-mix(in_srgb,var(--modira-teal)_70%,transparent)] hover:-translate-y-0.5',
  secondary:
    'glass text-fg hover:border-modira-cyan/40 hover:-translate-y-0.5',
  ghost: 'text-fg hover:text-fg',
};

export function Button({ variant = 'primary', children, className = '', ...props }: ButtonProps) {
  return (
    <a className={`${base} ${variants[variant]} ${className}`} {...props}>
      {children}
    </a>
  );
}
