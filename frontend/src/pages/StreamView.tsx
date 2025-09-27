import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import ItemCard from '../components/ItemCard';
import { api } from '../lib/api';
import { Button } from '../components/ui/button';
import { Dialog, DialogHeader, DialogBody, DialogFooter } from '../components/ui/dialog';
import { Select } from '../components/ui/select';

type ApiCuration = { title: string; hook: string; body_md?: string; links: { url: string; title?: string; domain?: string }[]; position: number };
type FeedRun = { id: string; started_at: string | null; finished_at?: string | null; run_at?: string | null; curations: ApiCuration[] };
type RunsRes = { runs: FeedRun[]; next_cursor?: string | null };

export default function StreamView() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [runs, setRuns] = useState<FeedRun[] | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState<boolean>(false);
  const [loadingMore, setLoadingMore] = useState<boolean>(false);
  // Run gating: disable Run Now while a run is in progress or after enqueue until latest finishes
  const [runDisabled, setRunDisabled] = useState<boolean>(false);
  const [runHoverHint, setRunHoverHint] = useState<string | undefined>(undefined);
  const baselineStartedAtRef = useRef<string | null>(null);
  const runRequestedRef = useRef<boolean>(false);
  const [meta, setMeta] = useState<{ name: string; description: string } | null>(null);
  const [streamInfo, setStreamInfo] = useState<{ mission: string; sources?: string; cadence?: string } | null>(null);
  const [editing, setEditing] = useState(false);
  const [metaLoaded, setMetaLoaded] = useState(false);
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setMetaLoaded(false);
    if (!id) return;
    (async () => {
      try {
        const s = await api.get<any>(`/streams/${encodeURIComponent(id)}`);
        if (!cancelled) {
          setMeta({ name: s.mission?.slice(0, 80) || 'Stream', description: s.mission || '' });
          setStreamInfo({ mission: s.mission || '', sources: s.sources_hints || '', cadence: s.cadence || 'weekly' });
        }
      } catch (e: any) {
        if (!cancelled) {
          setMeta(null);
          setError('Failed to load stream. Please sign in again or try later.');
        }
      } finally {
        if (!cancelled) setMetaLoaded(true);
      }
    })();
    return () => { cancelled = true; };
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!id) return;
      try {
        const page = await api.get<RunsRes>(`/streams/${encodeURIComponent(id)}/runs?limit=5`);
        if (!cancelled) {
          setRuns(page.runs || []);
          setCursor(page.next_cursor || null);
          setHasMore(!!(page.runs && page.runs.length > 0 && page.next_cursor));
        }
      } catch (e: any) {
        if (!cancelled) {
          setError('Failed to load runs. Please sign in again or try later.');
          setRuns([]);
          setCursor(null);
          setHasMore(false);
        }
      }
    })();
    return () => { cancelled = true; };
  }, [id]);

  // Check latest run to initialize disabled state and establish baseline
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!id) return;
      try {
        const latest = await api.get<any>(`/streams/${encodeURIComponent(id)}/latest`);
        if (cancelled) return;
        const started = latest?.started_at || latest?.run_at || null;
        const finished = latest?.finished_at || null;
        baselineStartedAtRef.current = started;
        // Disable button if there is a run without finished_at
        const inProgress = Boolean(latest?.run_id && !finished);
        setRunDisabled(inProgress);
        setRunHoverHint(inProgress ? 'A run is in progress. Check back later.' : undefined);
      } catch {
        // best effort; leave as-is
      }
    })();
    return () => { cancelled = true; };
  }, [id]);

  const runNow = async () => {
    if (!id || runDisabled) return;
    try {
      await api.post(`/streams/${encodeURIComponent(id)}/run`);
      runRequestedRef.current = true;
      setRunDisabled(true);
      setRunHoverHint('Run scheduled. Check back later.');
    } catch (e: any) {
      setError(e?.message || 'Failed to run');
    }
  };

  const onUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !streamInfo) return;
    try {
      await api.put(`/streams/${encodeURIComponent(id)}`, {
        mission: streamInfo.mission,
        sources: (streamInfo.sources || '').trim() || undefined,
        cadence: streamInfo.cadence || 'weekly',
      });
      setMeta({ name: streamInfo.mission.slice(0, 80) || 'Stream', description: streamInfo.mission });
      setEditing(false);
    } catch (e: any) {
      setError(e?.message || 'Update failed');
    }
  };

  const onDelete = async () => {
    if (!id) return;
    const yes = window.confirm('Delete this stream? You can no longer see it in your list.');
    if (!yes) return;
    try {
      await api.del(`/streams/${encodeURIComponent(id)}`);
      setEditing(false);
      navigate('/streams', { state: { toast: 'Stream deleted' } });
    } catch (e: any) {
      setError(e?.message || 'Delete failed');
    }
  };

  const loadMore = async () => {
    if (!id || id === 'user-mission' || !cursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const page = await api.get<RunsRes>(`/streams/${encodeURIComponent(id)}/runs?limit=5&before=${encodeURIComponent(cursor)}`);
      setRuns((prev) => ([...(prev || []), ...(page.runs || [])]));
      setCursor(page.next_cursor || null);
      setHasMore(!!(page.runs && page.runs.length > 0 && page.next_cursor));
    } catch {
      // keep current state
    } finally {
      setLoadingMore(false);
    }
  };

  // Background poll latest while disabled to re-enable when the enqueued run completes
  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    let timer: number | null = null;

    async function checkLatest() {
      try {
        const latest = await api.get<any>(`/streams/${encodeURIComponent(id)}/latest`);
        if (cancelled) return;
        const started = latest?.started_at || latest?.run_at || null;
        const finished = latest?.finished_at || null;

        // If any run exists and has not finished, keep disabled
        if (latest?.run_id && !finished) {
          setRunDisabled(true);
          setRunHoverHint('A run is in progress. Check back later.');
          return;
        }

        // If we requested a run, only re-enable once a newer finished run appears
        if (runRequestedRef.current) {
          const baseline = baselineStartedAtRef.current;
          if (started && finished && (!baseline || new Date(started) > new Date(baseline))) {
            baselineStartedAtRef.current = started;
            runRequestedRef.current = false;
            setRunDisabled(false);
            setRunHoverHint(undefined);
            // Optionally refresh runs list to include the new run
            try {
              const page = await api.get<RunsRes>(`/streams/${encodeURIComponent(id)}/runs?limit=5`);
              setRuns(page.runs || []);
              setCursor(page.next_cursor || null);
              setHasMore(!!(page.runs && page.runs.length > 0 && page.next_cursor));
            } catch {
              // ignore fetch error here
            }
          }
          return;
        }

        // Not requested; and nothing in progress → ensure enabled
        setRunDisabled(false);
        setRunHoverHint(undefined);
      } catch {
        // ignore
      }
    }

    if (runDisabled || runRequestedRef.current) {
      // Check immediately, then every few seconds
      checkLatest();
      timer = window.setInterval(checkLatest, 4000);
    }
    return () => {
      cancelled = true;
      if (timer) window.clearInterval(timer);
    };
  }, [runDisabled, id]);

  // Normalize links coming from API to robustly handle minor schema/format drift.
  // Accepts url/href/link keys; adds https:// if missing; ignores malformed values.
  function normalizeLinks(rawLinks: any[] | undefined | null): { label: string; url: string }[] {
    const out: { label: string; url: string }[] = [];
    const seen = new Set<string>();
    const arr = Array.isArray(rawLinks) ? rawLinks : [];
    for (const r of arr) {
      const cand = (r && (r.url || r.href || r.link)) as unknown;
      if (typeof cand !== 'string') continue;
      let u = cand.trim();
      if (!u) continue;
      // Add scheme if missing
      if (/^https?:\/\//i.test(u)) {
        // ok
      } else if (/^\/\//.test(u)) {
        u = 'https:' + u;
      } else if (/^(www\.)?[a-z0-9][a-z0-9.-]+\.[a-z]{2,}(\/.*)?$/i.test(u)) {
        u = 'https://' + u.replace(/^\/*/, '');
      } else {
        continue; // ignore non-http URLs
      }
      if (seen.has(u)) continue;
      seen.add(u);
      const label = (r && (r.domain || r.title)) || 'Link';
      out.push({ label: String(label), url: u });
    }
    return out;
  }

  // Infinite scroll: auto-load when sentinel enters viewport
  useEffect(() => {
    if (!hasMore || loadingMore) return;
    const el = sentinelRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            // Trigger load, guard ensures no spam
            loadMore();
          }
        }
      },
      { root: null, rootMargin: '0px 0px 200px 0px', threshold: 0.1 }
    );
    obs.observe(el);
    return () => {
      obs.disconnect();
    };
  }, [hasMore, cursor, loadingMore]);

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
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-3xl font-semibold tracking-tight mb-1">{meta?.name || 'Loading…'}</h2>
              <p className="text-muted-foreground m-0">{meta?.description || ''}</p>
            </div>
            {id !== 'user-mission' && (
              <div className="flex items-center gap-2">
                <span title={runDisabled ? (runHoverHint || 'Run scheduled. Check back later.') : ''}>
                  <Button onClick={runNow} disabled={runDisabled} aria-disabled={runDisabled}>Run Now</Button>
                </span>
                <Button variant="ghost" aria-label="Stream options" title="Options" onClick={() => setEditing(true)}>⋯</Button>
              </div>
            )}
          </div>
          {error && <div role="alert" className="text-sm text-red-600 mt-2">{error}</div>}
        </div>
        <Dialog open={editing} onOpenChange={setEditing}>
          <DialogHeader title="Edit Stream" description="Update mission, sources, and cadence." />
          <DialogBody>
            <form id="stream-edit-form" className="grid gap-4" onSubmit={onUpdate}>
              <label htmlFor="mission">
                <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">Mission</div>
                <textarea id="mission" rows={4} value={streamInfo?.mission || ''} onChange={(e) => setStreamInfo((p) => ({ ...(p || {}), mission: e.target.value }))}
                  className="flex min-h-24 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" required />
              </label>
              <label htmlFor="sources">
                <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">Sources (optional)</div>
                <textarea id="sources" rows={3} value={streamInfo?.sources || ''} onChange={(e) => setStreamInfo((p) => ({ ...(p || { mission: '' }), sources: e.target.value }))}
                  className="flex min-h-20 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" />
              </label>
              <label htmlFor="cadence">
                <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">Cadence</div>
                <Select
                  id="cadence"
                  value={streamInfo?.cadence || 'weekly'}
                  onValueChange={(v) => setStreamInfo((p) => ({ ...(p || { mission: '' }), cadence: v }))}
                  options={[
                    { value: 'daily', label: 'Daily' },
                    { value: '3xweek', label: '3× Week' },
                    { value: 'weekly', label: 'Weekly' },
                    { value: 'discovery', label: 'On Discovery' },
                  ]}
                />
              </label>
            </form>
          </DialogBody>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
            <Button variant="destructive" onClick={onDelete}>Delete</Button>
            <Button type="submit" form="stream-edit-form">Save changes</Button>
          </DialogFooter>
        </Dialog>
        <section className="card-surface p-6">
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">Feed</div>
          <div className="grid gap-6">
            {runs === null && <div className="text-muted-foreground">Loading…</div>}
            {runs && runs.length === 0 && <div className="text-muted-foreground">No runs yet. Use Run Now to start the first run.</div>}
            {runs && runs.map((r) => {
              const ts = r.started_at || r.run_at || '';
              const when = ts ? new Date(ts).toLocaleString() : '';
              return (
                <div key={r.id} className="grid gap-3">
                  <div className="text-xs text-muted-foreground">{when}</div>
                  <div className="grid gap-3">
                    {r.curations.map((c, idx) => {
                      const links = normalizeLinks(c.links);
                      if (import.meta.env.DEV && (window as any).__IN_DEBUG_LINKS) {
                        // eslint-disable-next-line no-console
                        console.debug('[StreamView] curation', { title: c.title, raw: c.links, normalized: links });
                      }
                      const item = { title: c.title, summary: c.hook, bodyMd: c.body_md || undefined, links };
                      return <ItemCard key={r.id + ':' + idx} item={item as any} isNew={false} />;
                    })}
                  </div>
                </div>
              );
            })}
            {hasMore && (
              <>
                <div ref={sentinelRef} className="h-1" aria-hidden />
                <div className="flex justify-center">
                  <Button variant="outline" onClick={loadMore} disabled={loadingMore}>{loadingMore ? 'Loading…' : 'Load more'}</Button>
                </div>
              </>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
