import type { Item } from '../mocks/mock-data';
import ReactMarkdown from 'react-markdown';
import { Badge } from './ui/badge';

function domainFrom(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return ''; }
}

type RichItem = Item & { bodyMd?: string };

export default function ItemCard({ item, isNew = false }: { item: RichItem; isNew?: boolean }) {
  const first = item.links[0];
  const source = first ? domainFrom(first.url) : '';
  return (
    <article
      className="rounded-xl border bg-card p-5 shadow-sm transition-shadow hover:shadow-md"
      data-has-links={item.links.length > 0 ? 'true' : 'false'}
      data-first-url={first?.url || ''}
      role="group"
    >
      {isNew && <Badge variant="new" className="mb-2">New</Badge>}
      {first?.url ? (
        <a
          className="block text-lg font-semibold tracking-tight text-foreground underline-offset-4 hover:underline hover:text-primary"
          href={first.url}
          target="_blank"
          rel="noopener noreferrer"
        >
          {item.title}
        </a>
      ) : (
        <div className="block text-lg font-semibold tracking-tight text-foreground">{item.title}</div>
      )}
      {item.bodyMd ? (
        <div className="mt-1 prose prose-sm max-w-none text-foreground/90">
          <ReactMarkdown>{item.bodyMd}</ReactMarkdown>
        </div>
      ) : (
        <p className="mt-1 text-foreground/80">{item.summary}</p>
      )}
      <div className="mt-1 text-sm text-muted-foreground">
        {source ? `Source: ${source}` : ''}{item.links.length > 1 ? ` • Links: ${item.links.length}` : ''}
      </div>
      <div className="mt-2 text-sm text-muted-foreground">
        <a href="#" onClick={(e) => e.preventDefault()} className="mr-4 underline-offset-4 hover:underline hover:text-primary">Save</a>
        <a href="#" onClick={(e) => e.preventDefault()} className="mr-4 underline-offset-4 hover:underline hover:text-primary">Hide</a>
        <a href="#" onClick={(e) => e.preventDefault()} className="underline-offset-4 hover:underline hover:text-primary">More like this</a>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {item.links.map((l) => (
          <a
            key={l.url}
            href={l.url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-full border bg-muted px-2.5 py-1 text-xs text-muted-foreground hover:text-primary select-none"
          >
            {l.label}
          </a>
        ))}
      </div>
    </article>
  );
}
