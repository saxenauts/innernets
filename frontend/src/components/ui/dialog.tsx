import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';

export function Dialog({ open, onOpenChange, children }: { open: boolean; onOpenChange: (v: boolean) => void; children: React.ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onOpenChange(false);
    };
    if (open) document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onOpenChange]);
  if (!open) return null;
  return createPortal(
    <div className="fixed inset-0 z-[100]" aria-hidden={false}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px] opacity-100 transition-opacity" onClick={() => onOpenChange(false)} />
      <div className="absolute inset-0 flex items-end sm:items-center justify-center p-4">
        <div
          role="dialog"
          aria-modal="true"
          className="w-full sm:max-w-lg bg-[hsl(var(--card))] border rounded-xl shadow-xl transition-all duration-200 ease-out translate-y-0 opacity-100 sm:translate-y-0"
          tabIndex={-1}
        >
          {children}
        </div>
      </div>
    </div>,
    document.body
  );
}

export function DialogHeader({ title, description }: { title: string; description?: string }) {
  return (
    <div className="p-5 border-b">
      <h3 className="text-xl font-semibold tracking-tight">{title}</h3>
      {description && <p className="text-sm text-muted-foreground mt-1">{description}</p>}
    </div>
  );
}

export function DialogBody({ children }: { children: React.ReactNode }) {
  return <div className="p-5">{children}</div>;
}

export function DialogFooter({ children }: { children: React.ReactNode }) {
  return <div className="p-4 border-t flex justify-end gap-2">{children}</div>;
}
