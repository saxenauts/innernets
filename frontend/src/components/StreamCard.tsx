import { Link } from 'react-router-dom';
import type { Stream } from '../mocks/mock-data';

export default function StreamCard({ stream }: { stream: Stream }) {
  const count = stream.items?.length ?? 0;
  return (
    <Link to={`/streams/${encodeURIComponent(stream.id)}`} aria-label={`Open ${stream.name}`}
      className="group grid grid-cols-[1fr_auto] items-start gap-4 p-5 hover:bg-muted/40 transition-colors">
      <div>
        <h3 className="text-xl font-semibold tracking-tight">{stream.name}</h3>
        <p className="text-muted-foreground line-clamp-2 mt-1">{stream.description}</p>
        <div className="text-muted-foreground text-sm mt-2">{count} {count === 1 ? 'item' : 'items'}</div>
      </div>
      <div className="text-muted-foreground transition-all group-hover:text-primary group-hover:translate-x-0.5">→</div>
    </Link>
  );
}
