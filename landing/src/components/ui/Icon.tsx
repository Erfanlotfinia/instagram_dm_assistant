import { icons, type LucideProps } from 'lucide-react';

type IconProps = LucideProps & {
  /** A valid lucide-react icon name, e.g. "Inbox", "Sparkles". */
  name: string;
};

/**
 * Resolves a lucide icon by name so content files can reference icons as
 * plain strings. Falls back to a neutral dot if the name is unknown.
 */
export function Icon({ name, ...props }: IconProps) {
  const LucideIcon = icons[name as keyof typeof icons] ?? icons.Circle;
  return <LucideIcon aria-hidden="true" {...props} />;
}
