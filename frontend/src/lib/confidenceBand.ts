import type { BadgeTone } from '../components/ui/Badge';

export function confidenceBandTone(band: string): BadgeTone {
  switch (band) {
    case 'high':
    case 'success':
      return 'success';
    case 'medium':
    case 'warning':
      return 'warning';
    case 'low':
    case 'danger':
      return 'danger';
    default:
      return 'neutral';
  }
}
