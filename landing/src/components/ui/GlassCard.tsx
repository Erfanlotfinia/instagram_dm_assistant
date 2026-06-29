import type { HTMLAttributes, ReactNode } from 'react';

type GlassCardProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  strong?: boolean;
  hover?: boolean;
};

export function GlassCard({
  children,
  strong = false,
  hover = false,
  className = '',
  ...props
}: GlassCardProps) {
  return (
    <div
      className={`${strong ? 'glass-strong' : 'glass'} rounded-3xl ${
        hover
          ? 'transition-all duration-300 hover:-translate-y-1 hover:border-modira-cyan/30'
          : ''
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
