# Design — Minimal Playbook

Purpose: calm, editorial UI that’s link‑first and token‑driven. Keep it simple and consistent.

## Tokens (edit here)
- Location: `frontend/src/styles/globals.css` inside `:root` and the dark‑mode block.
- Core: `--background`, `--foreground`, `--primary`, `--secondary`, `--muted`, `--border`, `--ring`, `--radius`.
- Tip: adjust `--radius` for overall shape and `--primary` for accent; everything updates automatically.

## Components (what to use)
- Buttons and inputs: `components/ui/button`, `components/ui/input`.
- Badge: `components/ui/badge` for small, low‑ink tags (e.g., New).
- Select: `components/ui/select` for dropdowns (opaque surface; token‑mapped focus and hover states).
- Layout: use `container-page` and `card-surface` utility classes for width, padding, and surfaces.

## Try Ideas Quickly
- Colors: tweak token values in `globals.css`, save, and refresh. Example: accent hue → adjust `--primary` HSL.
- Corners: change `--radius` (e.g., `0rem` crisp, `0.75rem` soft) and verify buttons/cards update.
- Density: adjust paddings (e.g., `p-5` → `p-6`) or type sizes on sections; avoid ad‑hoc colors.
- Dark: test with system dark mode; tokens are defined in the `@media (prefers-color-scheme: dark)` block.
- Components: try variants by changing classes on Button/Input/Select; keep to token‑mapped classes.

## Guardrails
- No heavy chrome or gradients; thin borders and subtle shadows only.
- Use token‑mapped classes (`bg-background`, `text-foreground`, `ring-ring`, etc.).
- Keep focus visible; don’t remove ring styles.

### Layering / Overlays
- Menus and popovers must be fully opaque: use `bg-[hsl(var(--card))]` (or `bg-background`) with a subtle shadow.
- Add `isolate` on the trigger container and a high `z-index` (e.g., `z-[999]`) to avoid any parent borders/lines bleeding through.
- Avoid alpha colors and backdrop-blur on surfaces beneath overlays.

That’s it—small tokens, small components, consistent outputs.

* Use View Transitions API so old cards gracefully morph into new cards (no full-page flash).
* Loading = text skeletons; no spinner.

**Interactions**

* Hover/focus/active use color/underline changes and slight background step; no scale jumps.
* Respect `prefers-reduced-motion`: switch to opacity-only.

---

## 7) Library choices & how to keep them from looking like everyone else

**Good baseline:**

* **Radix Primitives** or **Ark UI** (unstyled) for accessibility + popovers/dialogs.
* **Your own CSS tokens** + utilities (Tailwind optional).
  If you use Tailwind, **disable** default radii/shadows and map to tokens:

  ```js
  // tailwind.config.js
  theme: {
    borderRadius: { DEFAULT: 'var(--radius)' },
    boxShadow: { DEFAULT: 'var(--shadow-1)' },
    colors: { /* map semantic tokens via CSS vars */ },
  }
  plugins: [
    // plugin to forbid 'rounded-xl', 'shadow-lg', 'bg-gradient-to-*'
  ]
  ```
* **Stylelint rule** (or eslint-plugin-tailwindcss) to ban class combos that cause “template soup” (`rounded-xl shadow-lg bg-gradient-to-b`).

**If you must use a component library (Mantine/Chakra/shadcn):**

* Turn off theme defaults; feed CSS variables for colors/spacing/type.
* Replace icon set or adjust stroke/size to avoid the stock look.
* Strip secondary button variants; keep one primary, one outline, one text.

---

## 8) Accessibility checklist (ship with the PR)

* Body text contrast ≥ AA; small text ≥ AA; muted text still legible on surfaces.
* Keyboard focus visible on every interactive element; tab order logical.
* Hit targets ≥ 40×40.
* Verify lanes are keyboard-scrollable with snap.
* Announce run completion politely (`aria-live="polite"`).

---

## 9) Implementation order (one afternoon pass)

1. Wire tokens and type scale; remove gradients; set container width.
2. Rebuild NavBar (brand left, single action right).
3. Rebuild Link Card with the structure above; apply hover/focus/active.
4. Add skeletons + empty/error states.
5. Add view transitions on run.
6. Optional: Reader overlay.

---

## 10) Guardrails to keep it modern

* No big shadows, no neumorphism, no glassmorphism.
* No rainbow gradients; accent appears on links and the one primary action.
* One radius value across the app.
* Two fonts, max. One display, one sans.
* Asymmetric whitespace is allowed; cards are not uniform bricks.

---

If you want, I can also generate a **stylelint config** that blocks the most common “AI-generated UI” class combos so the look stays intentional.

---

## 11) Tone & Palette (v1.1 update)

Goal: avoid the heavy blue/black cast; adopt a calm, low‑chroma palette that reads as “paper + ink + jade accent”. Keep tokens role‑based; set values in theming.

Guidance
- Neutrals: warm paper (off‑white) for background, soft paper‑2 for subtle separation, hairline line color for rules. No pure black backgrounds.
- Accent: jade/teal for primary accents (links and the one primary action). Use sparingly. Avoid saturated electric blues.
- Ink: near‑black for text; muted ink for chrome and meta. Ensure WCAG contrast.
- Dark mode: “dim” charcoal surfaces, not pitch black; keep contrast comfortable and chroma low.

Neuroscience primer (practical)
- Lower chroma lowers arousal; helps sustained reading. Keep accent usage sparse to reserve attention for links.
- Comfortable reading: 60–80ch measure, ~1.5 line height, ample vertical rhythm to reduce saccade effort.
- Predictable affordances: link color + underline on hover/focus improve recognition; visible focus rings reduce cognitive load for keyboard users.

Implementation note
- Keep CSS role tokens as in §3. Use CSS variables (globals.css) and Tailwind mapping; avoid ad‑hoc overrides or hard-coded hex in components.

---

## 12) shadcn Integration & Current Patterns (2025)

Approach
- Use shadcn/ui as a code generator atop Radix primitives; theme via CSS variables and Tailwind. Keep our role tokens primary; map them in Tailwind (`tailwind.config.ts`) and use `components.json` with `cssVariables: true`.
- Base components added: Button, Card, Input, Badge. Extend with Dialog/Popover when needed.

Theming (shadcn)
- Tailwind extends map to role tokens: `ink`, `paper`, `line`, `accent`, radii, shadows, and font families.
- Prefer OKLCH/OKLab mixing for subtle state colors; avoid hard-coded hex in components.

Patterns snapshot (from recent sources)
- Token-first design: centralize color/space/typography in tokens; drive both light and dark via variables.
- Editorial lists over card grids for browseable feeds; cardlessness reduces visual noise.
- View Transitions API for state changes; skeletons instead of spinners.
- Low-chroma palettes; accents used sparingly; neutral surfaces layered with hairline dividers.
- Radix primitives for accessible overlays; minimal chrome; clear focus states.

