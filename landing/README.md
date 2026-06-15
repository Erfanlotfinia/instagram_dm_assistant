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

**File:** [`src/index.css`](src/index.css)

Edit the `@theme` block for palette tokens (`--color-ink-900`, `--color-cyan-500`, etc.) and component utilities (`.glass`, `.text-gradient`, `.accent-gradient`).

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
- **Logo** — text/SVG wordmark; no image asset provided.

## Stack

- Vite + React 18 + TypeScript
- Tailwind CSS v4 (`@tailwindcss/vite`)
- `@fontsource/vazirmatn` — Persian font
- `lucide-react` — icons
