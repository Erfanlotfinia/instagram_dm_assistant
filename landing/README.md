# Modira Landing Page

Premium RTL Persian marketing site for **Modira** — an AI Social Media Admin OS for online shops.

Standalone from the product admin app in `frontend/`.

## Quick start

```bash
cd landing
npm install
npm run dev
```

Open [http://localhost:5174](http://localhost:5174) (default port; override with `LANDING_PORT`).

## Commands

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Vite dev server |
| `npm run build` | Typecheck + production build → `dist/` |
| `npm run preview` | Preview production build |
| `npm run typecheck` | TypeScript check only |

## Folder structure

```
landing/
├── index.html              # RTL, SEO, Open Graph meta
├── package.json
├── vite.config.ts
├── tsconfig.json
├── README.md
└── src/
    ├── main.tsx            # App entry
    ├── App.tsx             # Composes all sections
    ├── index.css           # Tailwind + brand tokens + utilities
    ├── content/
    │   └── site.ts         # ★ All copy, nav, CTAs, features
    ├── hooks/
    │   └── useReveal.ts    # Scroll-reveal IntersectionObserver
    └── components/
        ├── layout/         # Navbar, Footer, Section, Container
        ├── ui/               # Button, Badge, GlassCard, etc.
        ├── mockups/          # CSS/HTML dashboard mockups
        └── sections/         # Hero, Problem, Solution, …
```

## Where to edit

### Brand text & CTAs

**File:** [`src/content/site.ts`](src/content/site.ts)

| Object | What it controls |
|--------|------------------|
| `brand` | Name, taglines, slogans |
| `cta` | Primary/secondary/panel CTA labels and `href` |
| `nav` | Navbar anchor links |
| `hero`, `problem`, `solution`, … | Section copy |
| `footer` | Footer links and note |

Example — change the demo CTA link:

```ts
export const cta = {
  primary: { label: 'درخواست دمو', href: 'https://your-form.com' },
  panel: { label: 'ورود به پنل', href: 'http://localhost:5173/login' },
  // ...
};
```

Panel login URL is built from `VITE_FRONTEND_URL` (defaults to `http://localhost:5173`).

## Docker Compose

Landing runs alongside the product frontend on the shared `public` Docker network:

| Service | Host URL | Internal port |
|---------|----------|---------------|
| `landing` | http://localhost:5174 | 5174 |
| `frontend` | http://localhost:5173 | 5173 |

```bash
docker compose up landing frontend backend
```

Environment variables (optional, in `.env` or shell):

| Variable | Default | Purpose |
|----------|---------|---------|
| `LANDING_PORT` | `5174` | Port Vite listens on (local + container) |
| `LANDING_HOST_PORT` | `5174` | Host port mapped to `LANDING_PORT` in Docker |
| `FRONTEND_HOST_PORT` | `5173` | Host port for product frontend |
| `VITE_FRONTEND_URL` | `http://localhost:5173` | Target for **ورود به پنل** button |

Local dev (without Docker):

```bash
LANDING_PORT=5174 npm run dev
```

If you change `FRONTEND_HOST_PORT`, set `VITE_FRONTEND_URL` to match (e.g. `http://localhost:5180`).

### Colors & visual style

**Files:** [`src/index.css`](src/index.css) and the canonical [`../brand/04_brand_tokens/modira-brand-tokens.css`](../brand/04_brand_tokens/modira-brand-tokens.css).

Brand primitives (`--modira-*`) are imported from the central tokens file — never duplicated. `src/index.css` maps them into Tailwind's `@theme` (`--color-modira-*`) and adds a theme-aware semantic layer (`--c-*` → `--color-canvas`, `--color-fg`, `--color-surface`, `--color-border`, `--color-accent`, ...). Prefer semantic utilities (`text-fg`, `bg-canvas`, `border-border`, `text-muted`) in components so they adapt to the active theme; reserve `modira-*` brand classes for deliberate accents (teal/cyan, gradients, glows, text on `accent-gradient`).

Approved brand colors only:

| Token | Hex |
|-------|-----|
| modira-teal | `#147A81` |
| modira-teal-dark | `#0F5F66` |
| modira-navy | `#102A43` |
| modira-navy-deep | `#07182B` |
| modira-cyan | `#38BDF8` |
| modira-cream | `#F8F5EA` |
| modira-graphite | `#1F2937` |
| modira-white | `#FFFFFF` |
| modira-black | `#000000` |

### Theme (light / dark / system)

The landing site supports light and dark themes driven by `data-theme` on `<html>`.

- **Store:** [`src/stores/themeStore.ts`](src/stores/themeStore.ts) — `light` / `dark` / `system`, persisted to `localStorage` under the shared `modira:theme` key (same key as the admin frontend, so preferences sync across apps). Defaults to `dark` on first visit.
- **Toggle:** [`src/components/ui/ThemeToggle.tsx`](src/components/ui/ThemeToggle.tsx) — wired into the `Navbar` (desktop action row + mobile drawer). Cycles light → dark → system.
- **FOUC:** [`index.html`](index.html) sets `data-theme` from `localStorage` before first paint.
- **Tokens:** dark values (`:root, [data-theme='dark']`) and light values (`[data-theme='light']`) are defined in `src/index.css`. Brand accents (`modira-teal`, `modira-cyan`, `.accent-gradient`, `.text-gradient`) are theme-independent.

### SEO

**File:** [`index.html`](index.html) — `<title>`, meta description, Open Graph tags.

## Component overview

| Layer | Components | Role |
|-------|------------|------|
| **Layout** | `Navbar`, `Footer`, `Section`, `Container` | Page shell, sticky nav, scroll-reveal wrapper |
| **UI** | `Button`, `Badge`, `GlassCard`, `GradientText`, `SectionHeading`, `Icon` | Reusable primitives |
| **Mockups** | `CommandCenter`, `DashboardMockup`, `ChatBubble`, `ProductCard`, `OrderStatusCard`, `DecisionTrace`, `ChannelBadge`, `FlowDiagram` | Pure CSS/HTML product visuals |
| **Sections** | `Hero`, `Problem`, `Solution`, `Philosophy`, `Features`, `Scenarios`, `Channels`, `Catalog`, `Dashboard`, `AiTasks`, `Security`, `Pilot`, `FinalCta` | Landing page sections |

## Assumptions

- **Standalone project** — not integrated into `frontend/` routing.
- **CTAs** point to `#demo` / `#features` anchors; swap `href` in `site.ts` for real forms or contact URLs.
- **No external paid assets** — Vazirmatn (self-hosted) + lucide-react icons + CSS mockups.
- **Single-page** — no React Router; smooth anchor navigation.
- **Logo** — vector brand mark from the canonical pack at [`../brand/`](../brand/README.md); production copies live in [`public/brand/`](public/brand/) and are rendered via [`src/components/brand/Logo.tsx`](src/components/brand/Logo.tsx). Favicon, apple-touch-icon, and PWA manifest are wired in [`index.html`](index.html) and [`public/site.webmanifest`](public/site.webmanifest).

## Stack

- Vite + React 18 + TypeScript
- Tailwind CSS v4 (`@tailwindcss/vite`)
- `@fontsource/vazirmatn` — Persian font
- `lucide-react` — icons
