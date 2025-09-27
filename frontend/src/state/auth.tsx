import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { supabase, SUPABASE_ENABLED } from '../lib/supabase';

type SignUpResult = { hasSession: boolean };

type AuthContextType = {
  authed: boolean;
  userEmail?: string;
  ready: boolean;
  // Standard methods
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<SignUpResult>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | null>(null);

const KEY = 'in_authed_user'; // dev fallback only

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // Session-driven state when Supabase is enabled
  const [authed, setAuthed] = useState<boolean>(false);
  const [email, setEmail] = useState<string | undefined>(undefined);
  const [ready, setReady] = useState<boolean>(!SUPABASE_ENABLED);

  // Dev/test fallback when Supabase env is not configured
  useEffect(() => {
    if (!SUPABASE_ENABLED) {
      try {
        const raw = localStorage.getItem(KEY);
        if (raw) {
          const e = (JSON.parse(raw).email as string) || undefined;
          setEmail(e);
          setAuthed(!!e);
        }
      } catch {
        // ignore
      }
      setReady(true);
      return;
    }
    // Supabase session bootstrap
    let mounted = true;
    (async () => {
      const { data } = await supabase!.auth.getSession();
      if (!mounted) return;
      const s = data.session;
      setAuthed(!!s?.access_token);
      setEmail(s?.user?.email || undefined);
      setReady(true);
    })();
    const { data: sub } = supabase!.auth.onAuthStateChange((_event, session) => {
      setAuthed(!!session?.access_token);
      setEmail(session?.user?.email || undefined);
    });
    return () => {
      mounted = false;
      sub.subscription.unsubscribe();
    };
  }, []);

  const signIn = async (email: string, password: string) => {
    if (!SUPABASE_ENABLED) {
      // dev fallback only
      setEmail(email);
      setAuthed(true);
      localStorage.setItem(KEY, JSON.stringify({ email }));
      return;
    }
    const { error } = await supabase!.auth.signInWithPassword({ email, password });
    if (error) throw new Error(error.message || 'Sign in failed');
  };

  const signUp = async (email: string, password: string): Promise<SignUpResult> => {
    if (!SUPABASE_ENABLED) {
      // dev fallback only
      setEmail(email);
      setAuthed(true);
      localStorage.setItem(KEY, JSON.stringify({ email }));
      return { hasSession: true };
    }
    const { data, error } = await supabase!.auth.signUp({ email, password });
    if (error) throw new Error(error.message || 'Sign up failed');
    return { hasSession: !!data.session };
  };

  const logout = async () => {
    if (SUPABASE_ENABLED) {
      await supabase!.auth.signOut();
    }
    setEmail(undefined);
    setAuthed(false);
    localStorage.removeItem(KEY);
  };

  const value = useMemo<AuthContextType>(() => ({
    authed,
    userEmail: email,
    ready,
    signIn,
    signUp,
    logout,
  }), [authed, email, ready]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
