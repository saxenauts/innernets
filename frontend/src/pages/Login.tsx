import { FormEvent, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../state/auth';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { TextareaHTMLAttributes } from 'react';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { login } = useAuth();

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const em = email.trim();
    if (!em) return;
    try {
      // Try Supabase password grant (dev)
      const SUPABASE_URL = (import.meta as any).env?.VITE_SUPABASE_URL as string | undefined;
      const SUPABASE_ANON_KEY = (import.meta as any).env?.VITE_SUPABASE_ANON_KEY as string | undefined;
      if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
        // fallback to mock auth if env not present
        login(em);
        navigate('/streams');
        return;
      }
      setError(null);
      const res = await fetch(`${SUPABASE_URL.replace(/\/$/, '')}/auth/v1/token?grant_type=password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'apikey': SUPABASE_ANON_KEY,
          // Some Supabase deployments require Authorization header mirroring apikey
          'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
        },
        body: JSON.stringify({ email: em, password }),
      });
      if (!res.ok) {
        let detail = `Supabase login failed: ${res.status}`;
        try {
          const j = await res.json();
          if (j?.error_description) detail = j.error_description;
          else if (j?.msg) detail = j.msg;
          else if (j?.error) detail = `${j.error}: ${j?.error_description || j?.message || ''}`.trim();
        } catch {}
        setError(detail || `Supabase login failed (${res.status})`);
        return;
      }
      const data = await res.json();
      const token = data?.access_token as string | undefined;
      if (!token) throw new Error('No access_token');
      login(em, token);
      navigate('/streams');
    } catch (err) {
      // Surface the error when Supabase is configured so we don't proceed without a token
      const msg = err instanceof Error ? err.message : 'Login failed';
      setError(msg);
    }
  };

  return (
    <div className="container-page py-10">
      <div className="mx-auto max-w-lg card-surface p-6">
        <h2 className="text-2xl font-semibold tracking-tight">Welcome back</h2>
        <p className="text-muted-foreground">Sign in to start exploring Streams.</p>
        {error ? (
          <div role="alert" className="text-sm text-red-600 mt-3" aria-live="polite">
            {error}
          </div>
        ) : null}
        <form className="grid gap-4" onSubmit={onSubmit}>
          <label>
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1">Email</div>
            <Input type="email" autoComplete="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label>
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1">Password</div>
            <Input type="password" autoComplete="current-password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          <div className="flex justify-between items-center gap-3">
            <Link className="text-sm underline-offset-4 hover:underline text-muted-foreground" to="/signup">Create account</Link>
            <Button type="submit">Sign in</Button>
          </div>
        </form>
      </div>
      <p className="text-center text-xs text-muted-foreground mt-6">By signing in you agree to our minimal, privacy-first posture.</p>
    </div>
  );
}
