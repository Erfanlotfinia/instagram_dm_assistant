import { Button } from './ui';
import { cn } from '../lib/cn';

interface PaginationProps {
  page: number;
  pageSize: number;
  totalItems: number;
  onPageChange: (page: number) => void;
  className?: string;
}

export function Pagination({ page, pageSize, totalItems, onPageChange, className }: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const start = totalItems === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, totalItems);

  if (totalItems <= pageSize) {
    return null;
  }

  return (
    <div className={cn('flex flex-wrap items-center justify-between gap-3 border-t border-border px-4 py-3', className)}>
      <p className="text-xs text-muted">
        Showing {start}–{end} of {totalItems}
      </p>
      <div className="flex items-center gap-2">
        <Button variant="secondary" size="sm" type="button" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          Previous
        </Button>
        <span className="min-w-[5rem] text-center text-xs tabular-nums text-muted">
          Page {page} of {totalPages}
        </span>
        <Button
          variant="secondary"
          size="sm"
          type="button"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          Next
        </Button>
      </div>
    </div>
  );
}

export function paginateItems<T>(items: T[], page: number, pageSize: number): T[] {
  const start = (page - 1) * pageSize;
  return items.slice(start, start + pageSize);
}

export function filterBySearch<T>(items: T[], getText: (item: T) => string, search: string): T[] {
  const term = search.trim().toLowerCase();
  if (!term) {
    return items;
  }
  return items.filter((item) => getText(item).toLowerCase().includes(term));
}
