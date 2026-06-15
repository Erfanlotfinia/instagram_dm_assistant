import type { ReactNode } from 'react';

import { useReveal } from '../../hooks/useReveal';
import { Container } from './Container';

type SectionProps = {
  id?: string;
  children: ReactNode;
  className?: string;
  /** Set false to render full-bleed content without the centered container. */
  contained?: boolean;
};

export function Section({ id, children, className = '', contained = true }: SectionProps) {
  const { ref, isVisible } = useReveal<HTMLDivElement>();

  return (
    <section id={id} className={`relative py-20 sm:py-28 ${className}`}>
      <div ref={ref} className={`reveal ${isVisible ? 'is-visible' : ''}`}>
        {contained ? <Container>{children}</Container> : children}
      </div>
    </section>
  );
}
