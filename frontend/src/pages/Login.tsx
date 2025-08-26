import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../state/auth';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();
  const { login } = useAuth();

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    // Mock auth
    if (email.trim()) {
      login(email.trim());
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
            <Input type="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label>
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1">Password</div>
            <Input type="password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          <div className="flex justify-end gap-3"><Button type="submit">Sign in</Button></div>
        </form>
      </div>
      <p className="text-center text-xs text-muted-foreground mt-6">By signing in you agree to our minimal, privacy-first posture.</p>
    </div>
  );
}
