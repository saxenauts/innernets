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

Auth flow (dev)
- Login page performs a Supabase password grant using `VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY` to obtain a short‑lived access token.
- The access token is stored in `localStorage` and sent as `Authorization: Bearer <token>` to the backend API.

Streams integration
- Onboarding (Create Stream) → `POST /streams` on the backend, then navigates to `/streams/:id`.
- Streams list → `GET /streams`.
- Stream view → `GET /streams/:id/latest` and a “Run Now” button performs `POST /streams/:id/run`.
- Curations render with markdown bodies when available (`body_md`), using `react-markdown`. Links are shown as chips beneath each item.
