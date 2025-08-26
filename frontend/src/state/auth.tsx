import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

type AuthContextType = {
  authed: boolean;
  login: (email: string) => void;
  logout: () => void;
  userEmail?: string;
};

const AuthContext = createContext<AuthContextType | null>(null);

const KEY = 'in_authed_user';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [email, setEmail] = useState<string | undefined>();

  useEffect(() => {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      try { setEmail(JSON.parse(raw).email as string); } catch {}
    }
  }, []);

  const value = useMemo<AuthContextType>(() => ({
    authed: !!email,
    userEmail: email,
    login: (e: string) => {
      setEmail(e);
      localStorage.setItem(KEY, JSON.stringify({ email: e }));
    },
    logout: () => {
      setEmail(undefined);
      localStorage.removeItem(KEY);
    }
  }), [email]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

