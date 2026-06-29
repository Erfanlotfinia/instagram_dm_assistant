import { Icon } from './Icon';
import { useTheme } from '../../stores/themeStore';

const NEXT_LABEL = {
  light: 'Switch to dark theme',
  dark: 'Switch to system theme',
  system: 'Switch to light theme',
} as const;

const ICON_NAME = {
  light: 'Sun',
  dark: 'Moon',
  system: 'Monitor',
} as const;

export function ThemeToggle({ className }: { className?: string }) {
  const { preference, cycle } = useTheme();

  return (
    <button
      type="button"
      onClick={cycle}
      title={`Theme: ${preference}`}
      aria-label={NEXT_LABEL[preference]}
      className={
        className ??
        'grid size-10 place-items-center rounded-xl border border-border text-muted transition-colors hover:bg-surface-sunken hover:text-fg'
      }
    >
      <Icon name={ICON_NAME[preference]} size={18} />
    </button>
  );
}
