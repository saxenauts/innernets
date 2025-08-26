# Frontend (Web) — Minimal Guide

## What’s here
- Pages: `Login`, `Onboarding`, `Streams`, `StreamView`.
- Components: `NavBar`, `StreamCard`, `ItemCard`, UI: `Button`, `Input`, `Badge`, `Select`.
- State: `AuthProvider` (localStorage-backed).
- Styles: `src/styles/globals.css` (Tailwind v4 + CSS variables).

## Commands
- `npm run dev` — start Vite.
- `npm run build` — type-check + build.
- `npm run preview` — serve the build.
- `npm run test` — unit tests (jsdom).

## Theming
- Edit tokens in `src/styles/globals.css` under `:root` (e.g., `--background`, `--foreground`, `--primary`, `--radius`).
- Dark mode follows system; tokens in the `@media (prefers-color-scheme: dark)` block.

## Patterns
- Layout: use `container-page` for width and padding.
- Surfaces: use `card-surface` or `rounded-xl border bg-card ...` with small shadows.
- Interactive: `Button`, `Input`, `Select` use the same token-bound classes for a consistent look.

### Overlays
- For dropdowns/menus, wrap the trigger in a `relative isolate` container.
- Render the menu as an absolute, high `z-index` element with `bg-[hsl(var(--card))]` and a small shadow.
- Avoid translucent surfaces beneath overlays to prevent bleed-through.

## Flows
- Login (`/`): mock auth → onboarding.
- Onboarding (`/onboarding`): capture `mission`, optional `sources`, and `cadence` (via Select); values persist to localStorage.
- Streams (`/streams`): list mission (if any) + mock streams.
- StreamView (`/streams/:id`): shows items with external links; first few marked “New”.

## Notes
- No legacy classes remain (e.g., `.hero`, `.panel`, `.btn`).
- Keep changes small and token-driven; avoid ad-hoc colors.

See `docs/updates.md` for change history.
