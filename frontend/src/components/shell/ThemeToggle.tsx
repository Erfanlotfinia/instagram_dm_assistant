import { Icons } from '../icons';
import { useTheme } from '../../stores/themeStore';

const NEXT_LABEL = {
  light: 'Switch to dark theme',
  dark: 'Switch to system theme',
  system: 'Switch to light theme',
} as const;

export function ThemeToggle() {
  const { preference, resolved, cycle } = useTheme();

  const icon =
    preference === 'system' ? <Icons.monitor size={18} /> : resolved === 'dark' ? <Icons.moon size={18} /> : <Icons.sun size={18} />;

  return (
    <button
      type="button"
      onClick={cycle}
      title={`Theme: ${preference}`}
      aria-label={NEXT_LABEL[preference]}
      className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border text-muted hover:bg-surface-sunken hover:text-fg"
    >
      {icon}
    </button>
  );
}
