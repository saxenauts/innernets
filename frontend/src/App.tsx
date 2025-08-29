import { Navigate, Route, Routes } from 'react-router-dom';
import NavBar from './components/NavBar';
import Login from './pages/Login';
import SignUp from './pages/SignUp';
import Onboarding from './pages/Onboarding';
import Streams from './pages/Streams';
import StreamView from './pages/StreamView';
import { AuthProvider, useAuth } from './state/auth';

function Protected({ children }: { children: JSX.Element }) {
  const { authed } = useAuth();
  if (!authed) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <NavBar />
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/signup" element={<SignUp />} />
        <Route path="/onboarding" element={<Protected><Onboarding /></Protected>} />
        <Route path="/streams" element={<Protected><Streams /></Protected>} />
        <Route path="/streams/:id" element={<Protected><StreamView /></Protected>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
