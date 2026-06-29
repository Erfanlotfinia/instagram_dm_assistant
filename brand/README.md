# Modira Brand

Canonical source-of-truth for the Modira visual identity. This folder holds the
rebuilt vector brand pack plus the derived color tokens.

## Layout

| Path | Contents |
|------|----------|
| `00_source_svg/` | Editable SVG source: symbol, wordmark, horizontal/vertical lockups (full-color, white-reversed, black), app icon, favicon, brand board. |
| `01_png_exports/` | Production PNG exports of the SVG source. |
| `02_icons_favicons/` | App icon sizes (16–1024), `apple-touch-icon.png`, `favicon.ico`, transparent symbol PNGs, and `site.webmanifest`. |
| `04_brand_tokens/` | `modira-brand-tokens.css` — the canonical brand color custom properties. |
| `05_docs/` | The original brand pack documentation (`README.md`). |

## Color tokens

The approved palette lives in [`04_brand_tokens/modira-brand-tokens.css`](04_brand_tokens/modira-brand-tokens.css).
This file is the **single source of truth** for the `--modira-*` primitives — both
apps `@import` it directly so the hex values are never duplicated:

- [`landing/src/index.css`](../landing/src/index.css) — `@import '../../brand/04_brand_tokens/modira-brand-tokens.css'`; `@theme` maps `--color-modira-*` and a theme-aware `--c-*` semantic layer (`text-fg`, `bg-canvas`, `border-border`, ...).
- [`frontend/src/app/globals.css`](../frontend/src/app/globals.css) — `@import '../../../brand/04_brand_tokens/modira-brand-tokens.css'`; `@theme` maps `--color-modira-*` and the `--c-*` semantic layer.

When the palette changes, update `04_brand_tokens/modira-brand-tokens.css` only —
both apps pick it up via the import. `frontend/scripts/check-brand-colors.mjs`
enforces that no raw hex outside the approved set is introduced in `frontend/src`
or `landing/src` (the `brand/` folder is the canonical source and is not scanned).

### Docker

CSS imports resolve to `/brand/04_brand_tokens/modira-brand-tokens.css` inside
containers (`../../brand/...` from `landing/src`, `../../../brand/...` from
`frontend/src/app`). Dev compose bind-mounts `./brand/04_brand_tokens` there;
Dockerfiles copy the same path during image build. Build context is the **repo
root** (`context: .`, `dockerfile: landing/Dockerfile` / `frontend/Dockerfile`).
After changing tokens or Dockerfiles, rebuild: `docker compose up --build landing frontend`.

## Production usage

Per `05_docs/README.md`, the recommended primary assets are:

- Primary website / header logo: `00_source_svg/modira_logo_horizontal_full_color.svg`
- Dark background logo: `00_source_svg/modira_logo_horizontal_white_reversed.svg`
- App icon: `00_source_svg/modira_app_icon.svg`
- Favicon: `02_icons_favicons/favicon.ico`
- Color tokens: `04_brand_tokens/modira-brand-tokens.css`

Production copies of these assets are placed under `landing/public/` and
`frontend/public/` so Vite serves them at the site root. Edit the SVGs here in
`brand/`, then re-copy into the per-app `public/` folders.

## Accessibility

When the logo is linked to the homepage, use alt text such as `Modira home`.
When the nearby text already says Modira, the symbol can be treated as
decorative (`alt=""`).
