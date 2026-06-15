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
          ? 'border-cyan-400/40 bg-cyan-500/15 text-cyan-300'
          : 'border-mist-200/10 bg-white/5 text-mist-300'
      }`}
    >
      <Icon name={icon} size={iconSize} />
    </span>
  );
}
