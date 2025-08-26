import * as React from 'react';
import { cn } from '../../lib/utils';

export type SelectOption = { value: string; label: string };

type SelectProps = {
  id?: string;
  value: string;
  onValueChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  className?: string;
};

export function Select({ id, value, onValueChange, options, placeholder = 'Select…', className }: SelectProps) {
  const [open, setOpen] = React.useState(false);
  const [highlight, setHighlight] = React.useState<number>(() => Math.max(0, options.findIndex((o) => o.value === value)));
  const rootRef = React.useRef<HTMLDivElement>(null);
  const listId = React.useId();

  React.useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current) return;
      if (!rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  React.useEffect(() => {
    if (open) {
      const idx = options.findIndex((o) => o.value === value);
      setHighlight(Math.max(0, idx));
    }
  }, [open, value, options]);

  const selected = options.find((o) => o.value === value) ?? null;

  const onKeyDownButton = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      setOpen((v) => !v);
    }
  };

  const onKeyDownList = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlight((h) => Math.min(options.length - 1, h + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlight((h) => Math.max(0, h - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const opt = options[highlight];
      if (opt) {
        onValueChange(opt.value);
        setOpen(false);
      }
    } else if (e.key === 'Escape' || e.key === 'Tab') {
      setOpen(false);
    }
  };

  // Note: `isolate` creates a new stacking context so the menu can layer above
  // surrounding borders/shadows without blending with translucent parents.
  return (
    <div ref={rootRef} className={cn('relative isolate', className)}>
      <button
        id={id}
        type="button"
        className={cn(
          'h-10 w-full rounded-lg border border-input bg-background px-3 pr-9 text-left text-sm text-foreground',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          'flex items-center justify-between'
        )}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => setOpen((v) => !v)}
        onKeyDown={onKeyDownButton}
      >
        <span className={cn('truncate', !selected && 'text-muted-foreground')}>{selected ? selected.label : placeholder}</span>
        <span aria-hidden className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground">▾</span>
      </button>
      {open && (
        // Opaque, high z-index surface to prevent any bleed-through.
        // Using token-mapped HSL explicitly ensures Safari/Tailwind edge cases
        // don't yield a semi-transparent panel.
        <div
          id={listId}
          role="listbox"
          tabIndex={-1}
          className={cn(
            'absolute left-0 z-[999] mt-1 w-full rounded-lg border border-input p-1 shadow-lg outline-none',
            'bg-[hsl(var(--card))]',
            'max-h-64 overflow-auto'
          )}
          style={{ backgroundColor: 'hsl(var(--card))' }}
          onKeyDown={onKeyDownList}
        >
          {options.map((opt, idx) => {
            const active = idx === highlight;
            const selected = opt.value === value;
            return (
              <div
                key={opt.value}
                role="option"
                aria-selected={selected}
                className={cn(
                  'cursor-pointer select-none rounded-md px-2.5 py-2 text-sm',
                  active ? 'bg-muted text-foreground' : 'text-foreground',
                  selected ? 'font-medium' : 'font-normal'
                )}
                onMouseEnter={() => setHighlight(idx)}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  onValueChange(opt.value);
                  setOpen(false);
                }}
              >
                {opt.label}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
