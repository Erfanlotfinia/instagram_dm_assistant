import type { ReactNode } from 'react';

import { GradientText } from './GradientText';

type SectionHeadingProps = {
  eyebrow?: string;
  title: ReactNode;
  subtitle?: ReactNode;
  align?: 'center' | 'start';
  className?: string;
};

export function SectionHeading({
  eyebrow,
  title,
  subtitle,
  align = 'center',
  className = '',
}: SectionHeadingProps) {
  const alignment = align === 'center' ? 'mx-auto text-center items-center' : 'text-start items-start';
  return (
    <div className={`flex max-w-3xl flex-col ${alignment} ${className}`}>
      {eyebrow ? (
        <span className="ltr mb-4 inline-flex items-center gap-2 rounded-full border border-cyan-400/25 bg-cyan-500/5 px-3 py-1 text-xs font-medium tracking-wide text-cyan-400">
          {eyebrow}
        </span>
      ) : null}
      <h2 className="text-balance text-2xl font-extrabold leading-tight text-mist-50 sm:text-3xl md:text-4xl">
        {title}
      </h2>
      {subtitle ? (
        <p className="mt-4 text-base leading-relaxed text-mist-400 sm:text-lg">{subtitle}</p>
      ) : null}
    </div>
  );
}

export { GradientText };
