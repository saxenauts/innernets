import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../state/auth';
import { Button } from './ui/button';

export default function NavBar() {
  const { authed, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <nav className="sticky top-0 z-50 bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/70 border-b">
      <div className="container-page flex items-center justify-between h-16">
        <NavLink to={authed ? '/streams' : '/'} className="font-semibold tracking-tight" aria-label="InnerNets home">
          Inner<span className="text-primary">Nets</span>
        </NavLink>
        <div className="flex items-center gap-2">
          {authed ? (
            <>
              <Button onClick={() => navigate('/onboarding')}>New Stream</Button>
              <Button variant="ghost" onClick={() => { logout(); navigate('/'); }}>Logout</Button>
            </>
          ) : (
            <div className="flex items-center gap-3">
              <NavLink to="/" className={({ isActive }) => (isActive ? 'text-foreground' : 'text-muted-foreground')}>Login</NavLink>
              <NavLink to="/signup" className={({ isActive }) => (isActive ? 'text-foreground' : 'text-muted-foreground')}>Sign up</NavLink>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
