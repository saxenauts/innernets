import { useEffect, useState } from 'react';
import StreamCard from '../components/StreamCard';
import { streams as baseStreams, type Stream } from '../mocks/mock-data';
import { api } from '../lib/api';

function fromOnboarding(): Stream | null {
  const mission = localStorage.getItem('in_onboarding_mission');
  if (!mission) return null;
  return {
    id: 'user-mission',
    name: 'Your Mission',
    description: mission,
    items: []
  };
}

export default function Streams() {
  const [list, setList] = useState<Stream[]>([]);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get<any[]>('/streams');
        const mapped: Stream[] = res.map((r) => ({ id: r.id, name: r.mission?.slice(0, 60) || 'Stream', description: r.mission || '', items: [] }));
        if (!cancelled) setList(mapped);
      } catch {
        const fallback: Stream[] = [fromOnboarding(), ...baseStreams].filter(Boolean) as Stream[];
        if (!cancelled) setList(fallback);
      }
    })();
    return () => { cancelled = true; };
  }, []);
  return (
    <div className="container-page py-10">
      <header className="mb-6">
        <h2 className="text-3xl font-semibold tracking-tight">Your Streams</h2>
        <p className="text-muted-foreground">Edited, link‑first outputs. “New since last run” appears in the stream view.</p>
      </header>
      <div className="card-surface divide-y divide-[hsl(var(--border))]">
        {list.map((s) => (
          <StreamCard key={s.id} stream={s} />
        ))}
      </div>
    </div>
  );
}
