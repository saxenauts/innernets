# Frontend (Web) — Minimal Guide

## What’s here
- Pages: `Login`, `SignUp`, `Onboarding`, `Streams`, `StreamView`.
- Components: `NavBar`, `StreamCard`, `ItemCard`, UI: `Button`, `Input`, `Badge`, `Select`.
- State: `AuthProvider` (session-backed via `@supabase/supabase-js`).
- Styles: `src/styles/globals.css` (Tailwind v4 + CSS variables).

## Commands
- `npm run dev` — start Vite.

- `npm run build` — type-check + build.
- `npm run preview` — serve the build.
- `npm run test` — unit tests (jsdom). Auth tests cover session gating (Protected), login/sign-up flows, and error banners on Streams.

## Theming
- Edit tokens in `src/styles/globals.css` under `:root` (e.g., `--background`, `--foreground`, `--primary`, `--radius`).
- Dark mode follows system; tokens in the `@media (prefers-color-scheme: dark)` block.

## Patterns
- Layout: use `container-page` for width and padding.
- Surfaces: use `card-surface` or `rounded-xl border bg-card ...` with small shadows.
- Interactive: `Button`, `Input`, `Select` use the same token-bound classes for a consistent look.

### Content & Links
- ItemCard renders markdown bodies (`body_md`) via `react-markdown` when available; otherwise falls back to the legacy `hook` text.
- Keep markdown simple: paragraphs, bold, and short lists. Inline links are not used in the body; anchors are rendered as chips below.
- Prefer native anchors for external URLs. Use `href`, `target="_blank"`, and `rel="noopener noreferrer"`.
- Do not use `window.open` in click handlers for normal links; it can be blocked by popup settings and interferes with middle/cmd-click semantics.
- Avoid parent container `onClick` that hijacks link clicks. Let anchors handle navigation.
- StreamView normalizes links (accepts `url|href|link` and adds `https://` for `www.`/schemeless). For debugging in dev, set `window.__IN_DEBUG_LINKS = true` and reload to log raw vs normalized links in the console.

### Overlays
- For dropdowns/menus, wrap the trigger in a `relative isolate` container.
- Render the menu as an absolute, high `z-index` element with `bg-[hsl(var(--card))]` and a small shadow.
- Avoid translucent surfaces beneath overlays to prevent bleed-through.

## Flows
- Login (`/`): uses `@supabase/supabase-js` (`signInWithPassword`). On success, navigates to Streams. If sign-in fails, the page surfaces the error and does not proceed.
- Onboarding (`/onboarding`): Create Stream via `POST /streams` (fields: `mission`, `sources`, `cadence`); navigate to `/streams/:id`. If API unavailable, falls back to localStorage for demo.
- Streams (`/streams`): loads from `GET /streams` (active only) with loader skeleton; shows an inline error banner on 401/5xx.
- StreamView (`/streams/:id`): reverse‑chronological feed via `GET /streams/:id/runs` (infinite scroll). Shows an error banner on 401/5xx. Edit/Delete and “Run Now” are available.
  - "Run Now" behavior: no inline status text. Button disables after enqueue and remains disabled while a run is pending/in‑progress; it re‑enables only after `/streams/:id/latest` reports a newer finished run. A plain tooltip (title attribute) on hover explains "Run scheduled. Check back later." when disabled.

## Notes
- No legacy classes remain (e.g., `.hero`, `.panel`, `.btn`).
- Keep changes small and token-driven; avoid ad-hoc colors.
- Auth sessions: supabase-js persists and refreshes sessions. After a long idle/background tab, the first request can 401 until refresh completes, then recover. This is expected for SPA flows; consider a backend cookie session later if zero transient 401s is a requirement.

## Accessibility
- Keep keyboard focus visible on every interactive element; do not remove focus rings.
- Dialogs/overlays: set `role="dialog"`, `aria-modal="true"`, and ensure escape closes. Prefer opaque surfaces; avoid translucency beneath.
- Labels: associate labels with inputs via `for`/`id`.
- Live regions: announce important status changes politely via `aria-live="polite"` (e.g., error banners).
- Hit targets: ≥ 40×40 logical pixels for tap/click targets.
- Contrast: ensure body text and small text meet WCAG AA.
- Reference: `docs/frontend-design.md` for the quick a11y checklist and design guardrails.

## Environment
- Create `frontend/.env.local` with:
  - `VITE_API_BASE_URL=http://localhost:8000`
  - `VITE_SUPABASE_URL=https://<your-supabase-ref>.supabase.co`
  - `VITE_SUPABASE_ANON_KEY=<your-anon-key>`

See `docs/updates.md` for change history.
