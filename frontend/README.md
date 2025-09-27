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
- Curations render with markdown bodies when available (`body_md`), using `react-markdown`. Links are shown as chips beneath each item.
