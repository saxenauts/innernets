import React, { createContext, useContext, useMemo, useState } from 'react';

type AuthContextType = {
  authed: boolean;
  login: (email: string, token?: string) => void;
  logout: () => void;
  userEmail?: string;
};

const AuthContext = createContext<AuthContextType | null>(null);

const KEY = 'in_authed_user';
const TOKEN_KEY = 'in_test_bearer';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [email, setEmail] = useState<string | undefined>(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return undefined;
      return (JSON.parse(raw).email as string) || undefined;
    } catch {
      return undefined;
    }
  });

  const value = useMemo<AuthContextType>(() => ({
    authed: !!email,
    userEmail: email,
    login: (e: string, token?: string) => {
      setEmail(e);
      localStorage.setItem(KEY, JSON.stringify({ email: e }));
      if (token && token.trim()) {
        localStorage.setItem(TOKEN_KEY, JSON.stringify({ token: token.trim() }));
      }
    },
    logout: () => {
      setEmail(undefined);
      localStorage.removeItem(KEY);
      localStorage.removeItem(TOKEN_KEY);
    }
  }), [email]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
