import { useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { streams } from '../mocks/mock-data';
import ItemCard from '../components/ItemCard';

export default function StreamView() {
  const { id } = useParams();
  const stream = useMemo(() => {
    if (id === 'user-mission') {
      const desc = localStorage.getItem('in_onboarding_mission') || 'Your saved mission';
      return { id, name: 'Your Mission', description: desc, items: [] };
    }
    return streams.find(s => s.id === id) || null;
  }, [id]);

  if (!stream) {
    return (
      <div className="container-page py-10">
        <div className="mx-auto max-w-xl card-surface p-6">
          <h3 className="text-2xl font-semibold tracking-tight">Stream not found</h3>
          <p className="text-muted-foreground mt-1">It may have been renamed or removed. Return to Streams.</p>
          <div className="mt-4">
            <Link to="/streams" className="underline-offset-4 hover:underline hover:text-primary">Back to Streams</Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container-page py-10">
      <div className="grid gap-4">
        <div className="card-surface p-6">
          <h2 className="text-3xl font-semibold tracking-tight mb-1">{stream.name}</h2>
          <p className="text-muted-foreground m-0">{stream.description}</p>
        </div>
        <section className="card-surface p-6">
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">Current</div>
          <div className="grid gap-3">
            {stream.items.map((it, idx) => (
              <ItemCard key={it.title + idx} item={it} isNew={idx < 3} />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
