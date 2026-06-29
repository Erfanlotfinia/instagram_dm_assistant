import { Icon } from '../ui/Icon';

type ChannelBadgeProps = {
  icon: string;
  name: string;
  size?: 'sm' | 'md';
  active?: boolean;
};

export function ChannelBadge({ icon, name, size = 'md', active = false }: ChannelBadgeProps) {
  const dim = size === 'sm' ? 'size-7' : 'size-9';
  const iconSize = size === 'sm' ? 14 : 18;
  return (
    <span
      title={name}
      className={`grid ${dim} place-items-center rounded-xl border transition-colors ${
        active
          ? 'border-modira-cyan/40 bg-modira-cyan/15 text-modira-cyan'
          : 'border-border bg-surface-sunken text-fg/80'
      }`}
    >
      <Icon name={icon} size={iconSize} />
    </span>
  );
}
