import type { ReactNode } from 'react';

type BadgeProps = {
  children: ReactNode;
  tone?: 'cyan' | 'emerald' | 'neutral';
  className?: string;
};

const tones = {
  cyan: 'border-cyan-400/30 bg-cyan-500/10 text-cyan-400',
  emerald: 'border-emerald-400/30 bg-emerald-500/10 text-emerald-400',
  neutral: 'border-mist-200/15 bg-white/5 text-mist-200',
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
