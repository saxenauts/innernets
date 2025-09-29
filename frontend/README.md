# Frontend (Vite + React)

Quick start
- Install: `cd frontend && npm install`
- Run dev: `npm run dev` (default at http://localhost:5173)

Environment variables (Vite)
- Create a file `frontend/.env.local` (ignored by git) with:

```
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=https://<your-supabase-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<your-supabase-anon-key>
```

Notes
- VITE_ prefix is required for variables to be exposed to the client in Vite.
- The Supabase anon key is intended for client-side use (it enforces RLS on the server). Do not put service role keys here.
- You can also use `.env`, `.env.development`, or `.env.local` depending on your workflow. `.env.local` is recommended for machine-specific values.

Auth flow
- Uses `@supabase/supabase-js` for session management. Login/SignUp call `supabase.auth.signInWithPassword`/`signUp`.
- The session is persisted by the library; API calls read the current access token and attach `Authorization: Bearer <token>` automatically.
- If email confirmation is required, SignUp shows a “Check your email” message and does not navigate to protected routes until confirmed/sign-in.

Streams integration
- Onboarding (Create Stream) → `POST /streams` on the backend, then navigates to `/streams/:id`.
- Streams list → `GET /streams`.
- Stream view → `GET /streams/:id/latest` and a “Run Now” button performs `POST /streams/:id/run`.
  - UX: no inline status text. The button disables after enqueue and remains disabled while a run is pending/in‑progress; it re‑enables when `/streams/:id/latest` reports a newer finished run. A simple hover tooltip on the disabled button explains that the run has been scheduled.
- Curations render with markdown bodies when available (`body_md`), using `react-markdown`. Links are shown as chips beneath each item.

Testing
- Run tests: `npm run test`
- What’s covered: auth gating (Protected), login/sign-up flows (including confirmation-required path), API error banners on Streams/StreamView, ItemCard link rendering, StreamView pagination (“Load more”), and Run Now gating.

Auth sessions & idle behavior
- supabase-js auto-refreshes sessions. After a long idle or when a tab is backgrounded or the device sleeps, browsers can throttle timers; the first API call on return may briefly use an expired access token and receive a 401 before the library refreshes in the background. A reload or a moment later requests succeed.
- This is expected in SPA setups. Options if needed later: trigger a session check on `visibilitychange` (tab focus) or move to a backend-managed cookie session to eliminate transient 401s.

Troubleshooting
- CORS error from browser
  - Symptom: fetch to `VITE_API_BASE_URL` blocked with a CORS message in DevTools.
  - Fix: ensure backend `CORS_ALLOW_ORIGINS` includes `http://localhost:5173` (or `*` for local only). Restart backend after changes.
- 401 Unauthorized after idle
  - Symptom: first request after returning to an idle/backgrounded tab 401s; a subsequent retry works.
  - Cause: access token expired while tab was throttled; supabase-js refreshes on activity.
  - Workaround: retry once on 401, or reload. Structural fix (later): move to a cookie session (BFF).
- Missing envs
  - Symptom: API base URL is `undefined` or login UI shows errors immediately.
  - Fix: create `.env.local` with `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, and `VITE_SUPABASE_ANON_KEY`. See `.env.example` for placeholders.

Dev proxy (optional)
- You can proxy API calls in dev instead of configuring backend CORS.
- Example (not enabled by default): add a `server.proxy` block to `vite.config.ts`.

```ts
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    open: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});
```

Then set `VITE_API_BASE_URL=/api` in `.env.local`.
