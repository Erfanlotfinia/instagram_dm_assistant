import type { ReactNode } from 'react';

type BadgeProps = {
  children: ReactNode;
  tone?: 'cyan' | 'emerald' | 'neutral';
  className?: string;
};

const tones = {
  cyan: 'border-modira-cyan/30 bg-modira-cyan/10 text-modira-cyan',
  emerald: 'border-modira-teal/30 bg-modira-teal/10 text-modira-teal',
  neutral: 'border-border bg-surface-sunken text-fg',
} as const;

export function Badge({ children, tone = 'neutral', className = '' }: BadgeProps) {
  return (
    <span
      className={`ltr inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${tones[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
