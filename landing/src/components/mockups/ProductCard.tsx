import { Icon } from '../ui/Icon';

type ProductCardProps = {
  name: string;
  price: string;
  meta?: string;
  inStock?: boolean;
  compact?: boolean;
};

export function ProductCard({ name, price, meta, inStock = true, compact = false }: ProductCardProps) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-border bg-surface-sunken p-3">
      <div className="grid size-12 shrink-0 place-items-center rounded-xl accent-gradient text-modira-navy-deep">
        <Icon name="Package" size={20} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-fg">{name}</p>
        {meta ? <p className="truncate text-xs text-muted">{meta}</p> : null}
        {!compact ? (
          <div className="mt-1.5 flex items-center gap-2">
            <span className="ltr text-sm font-bold text-modira-cyan">{price}</span>
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                inStock
                  ? 'bg-modira-teal/15 text-modira-teal'
                  : 'border border-border-strong bg-surface-sunken text-fg'
              }`}
            >
              <Icon name={inStock ? 'Check' : 'X'} size={10} />
              {inStock ? 'موجود' : 'ناموجود'}
            </span>
          </div>
        ) : (
          <span className="ltr mt-1 block text-sm font-bold text-modira-cyan">{price}</span>
        )}
      </div>
    </div>
  );
}
