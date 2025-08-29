import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../state/auth';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { TextareaHTMLAttributes } from 'react';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
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
        navigate('/onboarding');
        return;
      }
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
      if (!res.ok) throw new Error(`Supabase login failed: ${res.status}`);
      const data = await res.json();
      const token = data?.access_token as string | undefined;
      if (!token) throw new Error('No access_token');
      login(em, token);
      navigate('/onboarding');
    } catch (err) {
      // graceful fallback to mock auth
      login(em);
      navigate('/onboarding');
    }
  };

  return (
    <div className="container-page py-10">
      <div className="mx-auto max-w-lg card-surface p-6">
        <h2 className="text-2xl font-semibold tracking-tight">Welcome back</h2>
        <p className="text-muted-foreground">Sign in to start exploring Streams.</p>
        <form className="grid gap-4" onSubmit={onSubmit}>
          <label>
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1">Email</div>
            <Input type="email" autoComplete="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label>
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1">Password</div>
            <Input type="password" autoComplete="current-password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          <div className="flex justify-end gap-3"><Button type="submit">Sign in</Button></div>
        </form>
      </div>
      <p className="text-center text-xs text-muted-foreground mt-6">By signing in you agree to our minimal, privacy-first posture.</p>
    </div>
  );
}
