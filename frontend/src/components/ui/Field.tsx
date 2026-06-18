import type { InputHTMLAttributes, SelectHTMLAttributes, ReactNode } from 'react';

import { cn } from '../../lib/cn';

const controlClass =
  'h-9 w-full rounded-lg border border-border bg-surface px-3 text-sm text-fg placeholder:text-subtle focus:border-accent focus:outline-none';

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(controlClass, className)} {...props} />;
}

export function Select({
  className,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & { children: ReactNode }) {
  return (
    <select className={cn(controlClass, 'pr-8', className)} {...props}>
      {children}
    </select>
  );
}

interface FieldProps {
  label: ReactNode;
  htmlFor?: string;
  children: ReactNode;
  hint?: ReactNode;
  className?: string;
}

export function Field({ label, htmlFor, children, hint, className }: FieldProps) {
  return (
    <label htmlFor={htmlFor} className={cn('flex flex-col gap-1.5', className)}>
      <span className="text-xs font-medium text-muted">{label}</span>
      {children}
      {hint ? <span className="text-xs text-subtle">{hint}</span> : null}
    </label>
  );
}
