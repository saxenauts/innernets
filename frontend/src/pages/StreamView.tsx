import { useEffect, useMemo, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { streams } from '../mocks/mock-data';
import ItemCard from '../components/ItemCard';
import { api } from '../lib/api';
import { Button } from '../components/ui/button';

type ApiCuration = { title: string; hook: string; links: { url: string; title?: string; domain?: string }[]; position: number };
type LatestRes = { run_id: string | null; run_at: string | null; started_at?: string | null; finished_at?: string | null; curations: ApiCuration[] };

export default function StreamView() {
  const { id } = useParams();
  const [curations, setCurations] = useState<ApiCuration[] | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [meta, setMeta] = useState<{ name: string; description: string } | null>(null);
  const [metaLoaded, setMetaLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setMetaLoaded(false);
    if (!id) return;
    if (id === 'user-mission') {
      const desc = localStorage.getItem('in_onboarding_mission') || 'Your saved mission';
      if (!cancelled) {
        setMeta({ name: 'Your Mission', description: desc });
        setMetaLoaded(true);
      }
      return;
    }
    (async () => {
      try {
        const s = await api.get<any>(`/streams/${encodeURIComponent(id)}`);
        if (!cancelled) {
          setMeta({ name: s.mission?.slice(0, 80) || 'Stream', description: s.mission || '' });
        }
      } catch {
        if (!cancelled) setMeta(null);
      } finally {
        if (!cancelled) setMetaLoaded(true);
      }
    })();
    return () => { cancelled = true; };
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!id || id === 'user-mission') return;
      try {
        const latest = await api.get<LatestRes>(`/streams/${encodeURIComponent(id)}/latest`);
        if (!cancelled) setCurations(latest.curations);
      } catch {
        if (!cancelled) setCurations([]);
      }
    })();
    return () => { cancelled = true; };
  }, [id]);

  const runNow = async () => {
    if (!id || id === 'user-mission') return;
    setStatus('queued');
    try {
      await api.post(`/streams/${encodeURIComponent(id)}/run`);
      setStatus('queued');
    } catch (e: any) {
      setStatus(`error: ${e?.message || 'failed'}`);
    }
  };

  if (id !== 'user-mission' && metaLoaded && !meta) {
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
          <h2 className="text-3xl font-semibold tracking-tight mb-1">{meta?.name || 'Loading…'}</h2>
          <p className="text-muted-foreground m-0">{meta?.description || ''}</p>
          {id !== 'user-mission' && (
            <div className="mt-4 flex items-center gap-3">
              <Button onClick={runNow}>Run Now</Button>
              {status && <span className="text-sm text-muted-foreground">Status: {status}</span>}
            </div>
          )}
        </div>
        <section className="card-surface p-6">
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">Current</div>
          <div className="grid gap-3">
            {curations === null && <div className="text-muted-foreground">Loading…</div>}
            {curations && curations.length === 0 && <div className="text-muted-foreground">No curations yet. Use Run Now to start the first run.</div>}
            {curations && curations.map((c, idx) => {
              const item = {
                title: c.title,
                summary: c.hook,
                links: (c.links || []).map((l) => ({ label: l.domain || l.title || 'Link', url: l.url })),
              };
              return <ItemCard key={c.title + idx} item={item as any} isNew={idx < 3} />;
            })}
          </div>
        </section>
      </div>
    </div>
  );
}
