/**
 * One-time migration helper: replace hardcoded colors in styles.css with Modira semantic tokens.
 * Safe to re-run; already-migrated var() references are untouched.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const stylesPath = path.join(__dirname, '../src/app/styles.css');

/** @type {Record<string, string>} */
const HEX_MAP = {
  // Canvas / surface
  '#f6f7fb': 'var(--c-canvas)',
  '#f6f8fc': 'var(--c-surface-sunken)',
  '#fafbfd': 'var(--c-surface-sunken)',
  '#f8fafc': 'var(--c-surface-sunken)',
  '#eef1f7': 'var(--c-surface-sunken)',
  '#f2f4f7': 'var(--c-surface-sunken)',
  '#f1f3f9': 'var(--c-surface-sunken)',
  '#fff': 'var(--c-surface)',
  '#ffffff': 'var(--c-surface)',

  // Foreground text
  '#172033': 'var(--c-fg)',
  '#1d2939': 'var(--c-fg)',
  '#101828': 'var(--c-fg)',
  '#0f172a': 'var(--c-fg)',

  // Muted / secondary text
  '#6d7690': 'var(--c-muted)',
  '#4d5872': 'var(--c-muted)',
  '#475467': 'var(--c-muted)',
  '#667085': 'var(--c-muted)',
  '#344054': 'var(--c-muted)',
  '#98a2b3': 'var(--c-subtle)',
  '#9aa3b8': 'var(--c-subtle)',
  '#8b93a7': 'var(--c-subtle)',
  '#8a93a6': 'var(--c-subtle)',
  '#94a3b8': 'var(--c-subtle)',
  '#6b7790': 'var(--c-subtle)',

  // Borders
  '#e3e7ef': 'var(--c-border)',
  '#e3e8f0': 'var(--c-border)',
  '#e8ebf2': 'var(--c-border)',
  '#d7dce8': 'var(--c-border)',
  '#cdd5e3': 'var(--c-border-strong)',
  '#243049': 'var(--c-border)',
  '#33415c': 'var(--c-border-strong)',

  // Accent / primary (legacy blues → brand teal)
  '#2f5bff': 'var(--c-accent)',
  '#4f6bed': 'var(--c-accent)',
  '#7aa2ff': 'var(--c-accent)',
  '#9db8ff': 'var(--c-accent)',
  '#2563eb': 'var(--c-accent)',
  '#175cd3': 'var(--c-accent)',
  '#3730a3': 'var(--c-accent)',
  '#7a93ff': 'var(--c-accent)',
  '#5aa9f0': 'var(--c-info)',
  '#2b7fd4': 'var(--c-info)',

  // Accent soft backgrounds
  '#eaeefe': 'var(--c-accent-soft)',
  '#eef2ff': 'var(--c-accent-soft)',
  '#e8eeff': 'var(--c-accent-soft)',
  '#eef4ff': 'var(--c-accent-soft)',
  '#c7d7ff': 'var(--c-accent-soft)',
  '#1d2742': 'var(--c-accent-soft)',

  // Success
  '#067647': 'var(--c-success)',
  '#027a48': 'var(--c-success)',
  '#0f9d6b': 'var(--c-success)',
  '#166534': 'var(--c-success)',
  '#3ad29f': 'var(--c-success)',
  '#ecfdf3': 'var(--c-success-soft)',
  '#e3f7ee': 'var(--c-success-soft)',
  '#bbf7d0': 'var(--c-success-soft)',
  '#11271f': 'var(--c-success-soft)',

  // Warning
  '#c2850c': 'var(--c-warning)',
  '#b54708': 'var(--c-warning)',
  '#92400e': 'var(--c-warning)',
  '#e6b35a': 'var(--c-warning)',
  '#fffaeb': 'var(--c-warning-soft)',
  '#fef3c7': 'var(--c-warning-soft)',
  '#fde68a': 'var(--c-warning-soft)',
  '#fcf2dc': 'var(--c-warning-soft)',
  '#2b2110': 'var(--c-warning-soft)',

  // Danger
  '#b42318': 'var(--c-danger)',
  '#b91c1c': 'var(--c-danger)',
  '#d6453b': 'var(--c-danger)',
  '#ff6b61': 'var(--c-danger)',
  '#fef2f2': 'var(--c-danger-soft)',
  '#fecaca': 'var(--c-danger-soft)',
  '#fde8e8': 'var(--c-danger-soft)',
  '#fdecea': 'var(--c-danger-soft)',
  '#fef3f2': 'var(--c-danger-soft)',
  '#2c1513': 'var(--c-danger-soft)',

  // Info soft
  '#e7f1fb': 'var(--c-info-soft)',
  '#11243a': 'var(--c-info-soft)',

  // Dark surfaces (legacy)
  '#0b0f1a': 'var(--c-canvas)',
  '#131a29': 'var(--c-surface)',
  '#1a2333': 'var(--c-surface-raised)',
  '#0e1422': 'var(--c-surface-sunken)',
  '#26324c': 'var(--modira-navy)',
  '#e6ebf4': 'var(--c-fg)',

  // Misc legacy
  '#cbd2e0': 'var(--c-border)',
  '#5b6679': 'var(--c-muted)',
  '#64748b': 'var(--c-subtle)',
  '#475569': 'var(--c-subtle)',
  '#334155': 'var(--c-muted)',
  '#4b5469': 'var(--c-muted)',
  '#4b5563': 'var(--c-muted)',
  '#5b647a': 'var(--c-muted)',
  '#b0b7c3': 'var(--c-subtle)',
  '#b3b9c7': 'var(--c-subtle)',
  '#d0d5dd': 'var(--c-border)',
  '#d3d9e6': 'var(--c-border)',
  '#d7deea': 'var(--c-border)',
  '#d8deea': 'var(--c-border)',
  '#dfe3ec': 'var(--c-border)',
  '#e2e8f0': 'var(--c-border)',
  '#e4e7ec': 'var(--c-border)',
  '#e5e7eb': 'var(--c-border)',
  '#e8ecf4': 'var(--c-border)',
  '#c8d2e8': 'var(--c-border)',

  // Soft tinted backgrounds → semantic soft tokens
  '#f0fdf4': 'var(--c-success-soft)',
  '#dcfce7': 'var(--c-success-soft)',
  '#f6fdf9': 'var(--c-success-soft)',
  '#eef8f1': 'var(--c-success-soft)',
  '#cce8d6': 'var(--c-success-soft)',
  '#d1fae5': 'var(--c-success-soft)',
  '#abefc6': 'var(--c-success-soft)',
  '#86efac': 'var(--c-success-soft)',
  '#f0f7ff': 'var(--c-info-soft)',
  '#eff6ff': 'var(--c-info-soft)',
  '#f8faff': 'var(--c-info-soft)',
  '#f5f7ff': 'var(--c-info-soft)',
  '#f5f8ff': 'var(--c-info-soft)',
  '#f8fbff': 'var(--c-info-soft)',
  '#f7f9ff': 'var(--c-info-soft)',
  '#f0f4ff': 'var(--c-info-soft)',
  '#eff4ff': 'var(--c-info-soft)',
  '#eef3ff': 'var(--c-info-soft)',
  '#f2f5ff': 'var(--c-info-soft)',
  '#f4f6fb': 'var(--c-surface-sunken)',
  '#f9fafb': 'var(--c-surface-sunken)',
  '#f1f5f9': 'var(--c-surface-sunken)',
  '#f3f4f6': 'var(--c-surface-sunken)',
  '#fafffe': 'var(--c-surface)',
  '#fefce8': 'var(--c-warning-soft)',
  '#fef9c3': 'var(--c-warning-soft)',
  '#fedf89': 'var(--c-warning-soft)',
  '#fed7aa': 'var(--c-warning-soft)',
  '#fee2e2': 'var(--c-danger-soft)',
  '#fee4e2': 'var(--c-danger-soft)',
  '#fecdca': 'var(--c-danger-soft)',
  '#ffd8cc': 'var(--c-danger-soft)',
  '#f9d9d5': 'var(--c-danger-soft)',
  '#d6a7a2': 'var(--c-danger-soft)',

  // Blues/purples → accent
  '#3b6ef5': 'var(--c-accent)',
  '#5b8def': 'var(--c-accent)',
  '#6b8cff': 'var(--c-accent)',
  '#818cf8': 'var(--c-accent)',
  '#7a5af8': 'var(--c-accent)',
  '#5925dc': 'var(--c-accent)',
  '#4f46e5': 'var(--c-accent)',
  '#1e40af': 'var(--c-accent)',
  '#1e3a8a': 'var(--c-accent)',
  '#1e3a5f': 'var(--modira-navy)',
  '#2f3d5e': 'var(--modira-navy)',
  '#bfdbfe': 'var(--c-accent-soft)',
  '#c7d2fe': 'var(--c-accent-soft)',
  '#dbe4ff': 'var(--c-accent-soft)',
  '#dbeafe': 'var(--c-accent-soft)',
  '#d4def8': 'var(--c-accent-soft)',
  '#b8c9ff': 'var(--c-accent-soft)',
  '#93c5fd': 'var(--c-info)',
  '#f5f3ff': 'var(--c-accent-soft)',
  '#f4f3ff': 'var(--c-accent-soft)',
  '#d9d0fe': 'var(--c-accent-soft)',
  '#e3ebfb': 'var(--c-info-soft)',
  '#e9eefb': 'var(--c-info-soft)',
  '#b9e6fe': 'var(--c-info-soft)',
  '#f0f9ff': 'var(--c-info-soft)',
  '#0ba5ec': 'var(--c-info)',

  // Greens → success
  '#12b76a': 'var(--c-success)',
  '#22c55e': 'var(--c-success)',
  '#16a34a': 'var(--c-success)',
  '#10b981': 'var(--c-success)',
  '#34d399': 'var(--c-success)',

  // Oranges/yellows/reds → warning/danger
  '#f79009': 'var(--c-warning)',
  '#f59e0b': 'var(--c-warning)',
  '#fbbf24': 'var(--c-warning)',
  '#facc15': 'var(--c-warning)',
  '#ca8a04': 'var(--c-warning)',
  '#a16207': 'var(--c-warning)',
  '#78350f': 'var(--c-warning)',
  '#854d0e': 'var(--c-warning)',
  '#ef4444': 'var(--c-danger)',
  '#f04438': 'var(--c-danger)',
  '#f87171': 'var(--c-danger)',
  '#f97066': 'var(--c-danger)',
  '#dc2626': 'var(--c-danger)',
  '#d92d20': 'var(--c-danger)',
  '#991b1b': 'var(--c-danger)',
  '#912018': 'var(--c-danger)',
  '#7f1d1d': 'var(--c-danger)',
  '#9f1239': 'var(--c-danger)',
  '#7a5c58': 'var(--c-danger)',

  // Instagram gradient → brand accent
  '#833ab4': 'var(--modira-teal)',
  '#fd1d1d': 'var(--modira-cyan)',
  '#fcb045': 'var(--modira-teal-dark)',

  // Misc
  '#026aa2': 'var(--c-info)',
};

/** @type {Array<[RegExp, string]>} */
const RGBA_REPLACEMENTS = [
  [/rgba\(255,\s*255,\s*255,\s*0\.06\)/gi, 'color-mix(in srgb, var(--modira-white) 6%, transparent)'],
  [/rgba\(255,\s*255,\s*255,\s*0\.08\)/gi, 'color-mix(in srgb, var(--modira-white) 8%, transparent)'],
  [/rgba\(255,\s*255,\s*255,\s*0\.1\)/gi, 'color-mix(in srgb, var(--modira-white) 10%, transparent)'],
  [/rgba\(255,\s*255,\s*255,\s*0\.12\)/gi, 'color-mix(in srgb, var(--modira-white) 12%, transparent)'],
  [/rgba\(255,\s*255,\s*255,\s*0\.16\)/gi, 'color-mix(in srgb, var(--modira-white) 16%, transparent)'],
  [/rgba\(255,\s*255,\s*255,\s*0\.18\)/gi, 'color-mix(in srgb, var(--modira-white) 18%, transparent)'],
  [/rgba\(255,\s*255,\s*255,\s*0\.2\)/gi, 'color-mix(in srgb, var(--modira-white) 20%, transparent)'],
  [/rgba\(255,\s*255,\s*255,\s*0\.45\)/gi, 'color-mix(in srgb, var(--modira-white) 45%, transparent)'],
  [/rgba\(255,\s*255,\s*255,\s*0\.5\)/gi, 'color-mix(in srgb, var(--modira-white) 50%, transparent)'],
  [/rgba\(255,\s*255,\s*255,\s*0\.55\)/gi, 'color-mix(in srgb, var(--modira-white) 55%, transparent)'],
  [/rgba\(255,\s*255,\s*255,\s*0\.65\)/gi, 'color-mix(in srgb, var(--modira-white) 65%, transparent)'],
  [/rgba\(255,\s*255,\s*255,\s*0\.72\)/gi, 'color-mix(in srgb, var(--modira-white) 72%, transparent)'],
  [/rgba\(255,\s*255,\s*255,\s*0\.75\)/gi, 'color-mix(in srgb, var(--modira-white) 75%, transparent)'],
  [/rgba\(255,\s*255,\s*255,\s*0\.8\)/gi, 'color-mix(in srgb, var(--modira-white) 80%, transparent)'],
  [/rgba\(255,\s*255,\s*255,\s*0\.96\)/gi, 'color-mix(in srgb, var(--modira-white) 96%, transparent)'],
  [/rgba\(0,\s*0,\s*0,\s*0\.6\)/gi, 'color-mix(in srgb, var(--modira-black) 60%, transparent)'],
  [/rgba\(0,\s*0,\s*0,\s*0\.85\)/gi, 'color-mix(in srgb, var(--modira-black) 85%, transparent)'],
  [/rgba\(0,\s*0,\s*0,\s*0\.9\)/gi, 'color-mix(in srgb, var(--modira-black) 90%, transparent)'],
  [/rgba\(15,\s*23,\s*42,\s*0\.06\)/gi, 'color-mix(in srgb, var(--modira-navy) 6%, transparent)'],
  [/rgba\(15,\s*23,\s*42,\s*0\.45\)/gi, 'color-mix(in srgb, var(--modira-navy-deep) 45%, transparent)'],
  [/rgba\(23,\s*32,\s*51,\s*0\.04\)/gi, 'var(--c-shadow)'],
  [/rgba\(23,\s*32,\s*51,\s*0\.08\)/gi, 'color-mix(in srgb, var(--modira-navy) 8%, transparent)'],
  [/rgba\(23,\s*32,\s*51,\s*0\.12\)/gi, 'color-mix(in srgb, var(--modira-navy) 12%, transparent)'],
  [/rgba\(23,\s*32,\s*51,\s*0\.18\)/gi, 'color-mix(in srgb, var(--modira-navy) 18%, transparent)'],
  [/rgba\(23,\s*32,\s*51,\s*0\.28\)/gi, 'color-mix(in srgb, var(--modira-navy) 28%, transparent)'],
  [/rgba\(23,\s*32,\s*51,\s*0\.45\)/gi, 'color-mix(in srgb, var(--modira-navy) 45%, transparent)'],
  [/rgba\(122,\s*162,\s*255,\s*0\.2\)/gi, 'color-mix(in srgb, var(--modira-cyan) 20%, transparent)'],
  [/rgba\(122,\s*162,\s*255,\s*0\.7\)/gi, 'color-mix(in srgb, var(--modira-cyan) 70%, transparent)'],
  [/rgba\(34,\s*197,\s*94,\s*0\.2\)/gi, 'color-mix(in srgb, var(--modira-teal) 20%, transparent)'],
  [/rgba\(245,\s*158,\s*11,\s*0\.2\)/gi, 'color-mix(in srgb, var(--modira-cyan) 20%, transparent)'],
  [/rgba\(239,\s*68,\s*68,\s*0\.2\)/gi, 'color-mix(in srgb, var(--modira-navy) 20%, transparent)'],
  [/rgba\(47,\s*91,\s*255,\s*0\.06\)/gi, 'color-mix(in srgb, var(--modira-teal) 6%, transparent)'],
  [/rgba\(129,\s*140,\s*248,\s*0\.25\)/gi, 'color-mix(in srgb, var(--modira-cyan) 25%, transparent)'],
  [/rgba\(59,\s*130,\s*246,\s*0\.08\)/gi, 'color-mix(in srgb, var(--modira-cyan) 8%, transparent)'],
  [/rgba\(37,\s*99,\s*235,\s*0\.12\)/gi, 'color-mix(in srgb, var(--modira-teal) 12%, transparent)'],
  [/rgba\(37,\s*99,\s*235,\s*0\.2\)/gi, 'color-mix(in srgb, var(--modira-teal) 20%, transparent)'],
  [/rgba\(30,\s*58,\s*138,\s*0\.12\)/gi, 'color-mix(in srgb, var(--modira-navy) 12%, transparent)'],
  [/rgba\(30,\s*58,\s*138,\s*0\.25\)/gi, 'color-mix(in srgb, var(--modira-navy) 25%, transparent)'],
  [/rgba\(15,\s*23,\s*42,\s*0\.12\)/gi, 'color-mix(in srgb, var(--modira-navy-deep) 12%, transparent)'],
];

let css = fs.readFileSync(stylesPath, 'utf8');

// Remove conflicting :root color/background block at top
css = css.replace(
  /^:root\s*\{\s*color:\s*[^;]+;\s*background:\s*[^;]+;\s*font-family:[^}]+\}\s*/m,
  '',
);

// Replace hex colors (longest first to avoid partial matches on #fff vs #ffffff)
const hexKeys = Object.keys(HEX_MAP).sort((a, b) => b.length - a.length);
for (const hex of hexKeys) {
  const re = new RegExp(hex.replace('#', '#'), 'gi');
  css = css.replace(re, HEX_MAP[hex]);
}

// Replace rgba patterns
for (const [re, replacement] of RGBA_REPLACEMENTS) {
  css = css.replace(re, replacement);
}

// Sidebar gradient → brand gradient
css = css.replace(
  /linear-gradient\(180deg,\s*#172033\s*0%,\s*#26324c\s*100%\)/gi,
  'linear-gradient(180deg, var(--modira-navy-deep) 0%, var(--modira-navy) 100%)',
);

// Remaining generic rgba(255,255,255,X) catch-all
css = css.replace(
  /rgba\(255,\s*255,\s*255,\s*(0?\.\d+|1)\)/gi,
  (_, alpha) => {
    const pct = Math.round(parseFloat(alpha) * 100);
    return `color-mix(in srgb, var(--modira-white) ${pct}%, transparent)`;
  },
);

// Remaining generic rgba(23,32,51,X) catch-all
css = css.replace(
  /rgba\(23,\s*32,\s*51,\s*(0?\.\d+|1)\)/gi,
  (_, alpha) => {
    const pct = Math.round(parseFloat(alpha) * 100);
    return `color-mix(in srgb, var(--modira-navy) ${pct}%, transparent)`;
  },
);

// White text on dark sidebar areas
css = css.replace(/(?<=color:\s*)var\(--c-surface\)(?=;)/g, (match, offset) => {
  // Keep surface for backgrounds; for sidebar link colors use white
  return match;
});

fs.writeFileSync(stylesPath, css);

const remaining = [...css.matchAll(/#([0-9a-fA-F]{3,8})\b/g)];
console.log(`Migration complete. Remaining hex colors: ${remaining.length}`);
if (remaining.length > 0) {
  const uniq = [...new Set(remaining.map((m) => m[0].toLowerCase()))];
  console.log('Unmapped:', uniq.slice(0, 30).join(', '));
}

const remainingRgba = [...css.matchAll(/rgba\(/gi)];
console.log(`Remaining rgba(): ${remainingRgba.length}`);
