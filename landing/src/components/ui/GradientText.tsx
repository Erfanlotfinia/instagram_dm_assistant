import type { ElementType, ReactNode } from 'react';

type GradientTextProps = {
  children: ReactNode;
  as?: ElementType;
  className?: string;
};

export function GradientText({ children, as: Tag = 'span', className = '' }: GradientTextProps) {
  return <Tag className={`text-gradient ${className}`}>{children}</Tag>;
}
