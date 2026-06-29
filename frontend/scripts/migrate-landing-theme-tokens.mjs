/**
 * One-off: remap landing brand color classes to theme-aware semantic tokens.
 *
 * Run once after introducing the landing --c-* semantic layer:
 *   node frontend/scripts/migrate-landing-theme-tokens.mjs
 *
 * Brand accents (modira-teal / modira-cyan, gradients, glows, and
 * text-modira-navy-deep used on accent-gradient surfaces) are intentionally
 * left theme-independent and are NOT rewritten here.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const landingSrc = path.join(__dirname, '../../landing/src');

/** @type {Array<[RegExp, string]>} */
const REPLACEMENTS = [
  // Text — specific opacity variants first, then bare class.
  [/text-modira-cream\/80\b/g, 'text-fg/80'],
  [/text-modira-cream\/65\b/g, 'text-muted'],
  [/text-modira-cream\/50\b/g, 'text-subtle'],
  [/hover:text-modira-cream\b/g, 'hover:text-fg'],
  [/text-modira-cream\b/g, 'text-fg'],

  // Borders.
  [/border-modira-cream\/25\b/g, 'border-border-strong'],
  [/border-modira-cream\/15\b/g, 'border-border'],
  [/border-modira-cream\/12\b/g, 'border-border'],
  [/border-modira-cream\/10\b/g, 'border-border'],
  [/border-modira-navy\/30\b/g, 'border-border-strong'],
  [/border-modira-navy\/25\b/g, 'border-border-strong'],

  // Backgrounds — canvas / surface / surface-sunken.
  [/bg-modira-navy-deep\b/g, 'bg-canvas'],
  [/bg-modira-navy\/40\b/g, 'bg-surface'],
  [/bg-modira-navy\/30\b/g, 'bg-surface'],
  [/bg-modira-navy\b/g, 'bg-surface'],
  [/bg-modira-graphite\/70\b/g, 'bg-surface'],
  [/bg-modira-graphite\/60\b/g, 'bg-surface'],
  [/bg-modira-graphite\/40\b/g, 'bg-surface-sunken'],
  [/bg-modira-graphite\/30\b/g, 'bg-surface-sunken'],
  [/bg-modira-white\/5\b/g, 'bg-surface-sunken'],
  [/bg-modira-white\/\[0\.02\]/g, 'bg-surface-sunken'],
  [/bg-modira-white\/\[0\.03\]/g, 'bg-surface-sunken'],
  [/hover:bg-modira-white\/5\b/g, 'hover:bg-surface-sunken'],
  [/hover:bg-modira-white\/\[0\.02\]/g, 'hover:bg-surface-sunken'],
];

function walk(dir) {
  /** @type {string[]} */
  const files = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) files.push(...walk(full));
    else if (/\.(tsx|ts|css)$/.test(entry.name)) files.push(full);
  }
  return files;
}

let touched = 0;
for (const file of walk(landingSrc)) {
  let content = fs.readFileSync(file, 'utf8');
  let changed = false;
  for (const [re, replacement] of REPLACEMENTS) {
    const next = content.replace(re, replacement);
    if (next !== content) {
      content = next;
      changed = true;
    }
  }
  if (changed) {
    fs.writeFileSync(file, content);
    touched += 1;
  }
}

console.log(`Landing theme-token migration complete. ${touched} file(s) updated.`);
