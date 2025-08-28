import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Select } from '../components/ui/select';
import { api } from '../lib/api';

const MISSION_KEY = 'in_onboarding_mission';
const SOURCES_KEY = 'in_onboarding_sources';
const CADENCE_KEY = 'in_onboarding_cadence';

export default function Onboarding() {
  const [mission, setMission] = useState<string>(localStorage.getItem(MISSION_KEY) || '');
  const [sources, setSources] = useState<string>(localStorage.getItem(SOURCES_KEY) || '');
  const [cadence, setCadence] = useState<string>(localStorage.getItem(CADENCE_KEY) || 'weekly');
  const navigate = useNavigate();

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const body = { mission: mission.trim(), sources_hints: sources.trim() || undefined, cadence };
      const created = await api.post<{ id: string }>('/streams', body);
      navigate(`/streams/${encodeURIComponent(created.id)}`);
    } catch (err) {
      // Fallback to local storage if API unavailable
      localStorage.setItem(MISSION_KEY, mission.trim());
      localStorage.setItem(SOURCES_KEY, sources.trim());
      localStorage.setItem(CADENCE_KEY, cadence);
      navigate('/streams');
    }
  };

  return (
    <div className="container-page py-10">
      <div className="mx-auto max-w-2xl card-surface p-6">
        <h2 className="text-3xl font-semibold tracking-tight mb-1">Set your first Stream</h2>
        <p className="text-muted-foreground mb-6">Name your mission and cadence. Hint sources inline (e.g., “favor arXiv; avoid listicles”).</p>
        <form className="grid gap-5" onSubmit={onSubmit}>
          <label htmlFor="mission">
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">Mission</div>
            <textarea
              id="mission"
              rows={5}
              placeholder="e.g., AI tools with persistent user memory—what’s real & useful?"
              value={mission}
              onChange={(e) => setMission(e.target.value)}
              required
              className="flex min-h-28 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            />
          </label>
          <label htmlFor="sources">
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">Preferred sources (optional)</div>
            <textarea
              id="sources"
              rows={3}
              placeholder="e.g., show YouTube videos from Veritasium, PBS and similar channels; prefer original papers over magazines"
              value={sources}
              onChange={(e) => setSources(e.target.value)}
              className="flex min-h-20 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            />
          </label>
          <label htmlFor="cadence">
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">Cadence</div>
            <Select
              id="cadence"
              value={cadence}
              onValueChange={setCadence}
              options={[
                { value: 'daily', label: 'Daily' },
                { value: '3xweek', label: '3× Week' },
                { value: 'weekly', label: 'Weekly' },
                { value: 'discovery', label: 'On Discovery' }
              ]}
            />
          </label>
          <div className="flex justify-end">
            <Button type="submit">Create Stream</Button>
          </div>
        </form>
      </div>
    </div>
  );
}
