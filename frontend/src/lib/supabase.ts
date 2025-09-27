import { createClient, type SupabaseClient } from '@supabase/supabase-js';

const url = (import.meta as any).env?.VITE_SUPABASE_URL as string | undefined;
const anon = (import.meta as any).env?.VITE_SUPABASE_ANON_KEY as string | undefined;

export const SUPABASE_ENABLED = Boolean(url && anon);

export const supabase: SupabaseClient | null = SUPABASE_ENABLED
  ? createClient(url as string, anon as string)
  : null;

