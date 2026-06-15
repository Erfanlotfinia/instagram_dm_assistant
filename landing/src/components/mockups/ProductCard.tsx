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
    <div className="flex items-center gap-3 rounded-2xl border border-mist-200/10 bg-white/5 p-3">
      <div className="grid size-12 shrink-0 place-items-center rounded-xl accent-gradient text-ink-950">
        <Icon name="Package" size={20} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-mist-50">{name}</p>
        {meta ? <p className="truncate text-xs text-mist-400">{meta}</p> : null}
        {!compact ? (
          <div className="mt-1.5 flex items-center gap-2">
            <span className="ltr text-sm font-bold text-cyan-400">{price}</span>
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                inStock
                  ? 'bg-emerald-500/15 text-emerald-300'
                  : 'bg-rose-500/15 text-rose-300'
              }`}
            >
              <Icon name={inStock ? 'Check' : 'X'} size={10} />
              {inStock ? 'موجود' : 'ناموجود'}
            </span>
          </div>
        ) : (
          <span className="ltr mt-1 block text-sm font-bold text-cyan-400">{price}</span>
        )}
      </div>
    </div>
  );
}
