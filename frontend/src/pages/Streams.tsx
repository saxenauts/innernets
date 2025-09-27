import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import StreamCard from '../components/StreamCard';
type Stream = { id: string; name: string; description: string; items: any[] };
import { api } from '../lib/api';

export default function Streams() {
  const [list, setList] = useState<Stream[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const location = useLocation() as any;
  const navigate = useNavigate();
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get<any[]>('/streams');
        const mapped: Stream[] = res.map((r) => ({ id: r.id, name: r.mission?.slice(0, 60) || 'Stream', description: r.mission || '', items: [] }));
        if (!cancelled) setList(mapped);
      } catch (e: any) {
        if (!cancelled) {
          setError('Failed to load streams. Please sign in again or try later.');
          setList([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // One-off toast from navigation state
  useEffect(() => {
    const msg = location?.state?.toast as string | undefined;
    if (msg) {
      setToast(msg);
      // Clear state so refresh doesn't re-show
      navigate(location.pathname, { replace: true });
      const t = setTimeout(() => setToast(null), 3000);
      return () => clearTimeout(t);
    }
  }, [location?.state, location?.pathname]);
  return (
    <div className="container-page py-10">
      {toast && (
        <div role="alert" className="mb-4 rounded-lg border bg-green-50 px-4 py-3 text-green-900 shadow-sm">
          {toast}
        </div>
      )}
      {error && (
        <div role="alert" className="mb-4 rounded-lg border bg-red-50 px-4 py-3 text-red-900 shadow-sm">
          {error}
        </div>
      )}
      <header className="mb-6">
        <h2 className="text-3xl font-semibold tracking-tight">Your Streams</h2>
        <p className="text-muted-foreground">Edited, link‑first outputs. “New since last run” appears in the stream view.</p>
      </header>
      {loading ? (
        <div className="grid gap-3">
          {[0,1,2].map((i) => (
            <div key={i} className="card-surface p-5 animate-pulse">
              <div className="h-5 w-1/3 bg-muted rounded mb-2"></div>
              <div className="h-4 w-2/3 bg-muted rounded mb-1"></div>
              <div className="h-4 w-1/2 bg-muted rounded"></div>
            </div>
          ))}
        </div>
      ) : list.length === 0 ? (
        <div className="card-surface p-6">
          <div className="text-muted-foreground">No streams yet. Create your first stream from the New Stream button.</div>
        </div>
      ) : (
        <div className="card-surface divide-y divide-[hsl(var(--border))]">
          {list.map((s) => (
            <StreamCard key={s.id} stream={s} />
          ))}
        </div>
      )}
    </div>
  );
}
