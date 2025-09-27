import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../state/auth';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';

export default function SignUp() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { signUp } = useAuth();

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const em = email.trim();
    if (!em) return;
    try {
      setError(null);
      const res = await signUp(em, password);
      if (res.hasSession) {
        navigate('/onboarding');
      } else {
        setError('Check your email to confirm your account, then sign in.');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Sign up failed';
      setError(msg);
    }
  };

  return (
    <div className="container-page py-10">
      <div className="mx-auto max-w-lg card-surface p-6">
        <h2 className="text-2xl font-semibold tracking-tight">Create your account</h2>
        <p className="text-muted-foreground">Sign up and set your first Stream.</p>
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
            <Input type="password" autoComplete="new-password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          <div className="flex justify-between items-center gap-3">
            <a className="text-sm underline-offset-4 hover:underline text-muted-foreground" href="/">Have an account? Sign in</a>
            <Button type="submit">Sign up</Button>
          </div>
        </form>
      </div>
      <p className="text-center text-xs text-muted-foreground mt-6">We use email/password for demo; no social auth.</p>
    </div>
  );
}
