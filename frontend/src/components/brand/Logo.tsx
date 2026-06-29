type LogoVariant = 'mark' | 'lockup';

interface LogoProps {
  variant?: LogoVariant;
  className?: string;
  alt?: string;
}

const MARK_WHITE = '/brand/modira_symbol_white.svg';
const LOCKUP_FULL = '/brand/modira_logo_horizontal_full_color.svg';

export function Logo({ variant = 'mark', className, alt = '' }: LogoProps) {
  const src = variant === 'mark' ? MARK_WHITE : LOCKUP_FULL;
  const resolved = className ?? (variant === 'mark' ? 'h-5 w-auto' : 'h-8 w-auto');
  return <img src={src} alt={alt} className={resolved} draggable={false} />;
}
