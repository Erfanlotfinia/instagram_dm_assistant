type LogoVariant = 'mark' | 'lockup';

interface LogoProps {
  variant?: LogoVariant;
  reversed?: boolean;
  className?: string;
  alt?: string;
}

const MARK_FULL = '/brand/modira_symbol_full_color.svg';
const MARK_WHITE = '/brand/modira_symbol_white.svg';
const LOCKUP_FULL = '/brand/modira_logo_horizontal_full_color.svg';
const LOCKUP_REVERSED = '/brand/modira_logo_horizontal_white_reversed.svg';

export function Logo({
  variant = 'mark',
  reversed = false,
  className,
  alt = 'Modira',
}: LogoProps) {
  const src =
    variant === 'mark'
      ? reversed
        ? MARK_WHITE
        : MARK_FULL
      : reversed
        ? LOCKUP_REVERSED
        : LOCKUP_FULL;

  return (
    <img
      src={src}
      alt={alt}
      className={className}
      draggable={false}
    />
  );
}
