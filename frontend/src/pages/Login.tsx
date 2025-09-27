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
  const { signIn } = useAuth();

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const em = email.trim();
    if (!em) return;
    try {
      setError(null);
      await signIn(em, password);
      navigate('/streams');
    } catch (err) {
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
