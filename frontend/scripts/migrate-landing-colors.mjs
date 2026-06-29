/**
 * Bulk-replace legacy landing color class names with official Modira tokens.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const landingSrc = path.join(__dirname, '../../landing/src');

/** @type {Array<[RegExp, string]>} */
const REPLACEMENTS = [
  [/text-mist-50\b/g, 'text-modira-cream'],
  [/text-mist-100\b/g, 'text-modira-cream'],
  [/text-mist-200\b/g, 'text-modira-cream'],
  [/text-mist-300\b/g, 'text-modira-cream/80'],
  [/text-mist-400\b/g, 'text-modira-cream/65'],
  [/text-mist-500\b/g, 'text-modira-cream/50'],
  [/text-ink-950\b/g, 'text-modira-navy-deep'],
  [/text-cyan-200\b/g, 'text-modira-cyan'],
  [/text-cyan-300\b/g, 'text-modira-cyan'],
  [/text-cyan-400\b/g, 'text-modira-cyan'],
  [/text-emerald-200\b/g, 'text-modira-teal'],
  [/text-emerald-300\b/g, 'text-modira-teal'],
  [/text-emerald-400\b/g, 'text-modira-teal'],
  [/bg-ink-950\b/g, 'bg-modira-navy-deep'],
  [/bg-ink-900\b/g, 'bg-modira-navy'],
  [/bg-ink-800\b/g, 'bg-modira-navy'],
  [/bg-ink-700\b/g, 'bg-modira-graphite'],
  [/from-ink-900\b/g, 'from-modira-navy'],
  [/border-mist-200\/(\d+)/g, 'border-modira-cream/$1'],
  [/border-cyan-400\/(\d+)/g, 'border-modira-cyan/$1'],
  [/border-emerald-400\/(\d+)/g, 'border-modira-teal/$1'],
  [/bg-cyan-500\/(\d+)/g, 'bg-modira-cyan/$1'],
  [/bg-emerald-500\/(\d+)/g, 'bg-modira-teal/$1'],
  [/bg-teal-700\/(\d+)/g, 'bg-modira-teal-dark/$1'],
  [/via-cyan-400\/(\d+)/g, 'via-modira-cyan/$1'],
  [/from-cyan-500\/(\d+)/g, 'from-modira-cyan/$1'],
  [/from-emerald-500\/(\d+)/g, 'from-modira-teal/$1'],
  [/hover:text-cyan-200\b/g, 'hover:text-modira-cyan'],
  [/hover:text-cyan-300\b/g, 'hover:text-modira-cyan'],
  [/hover:text-cyan-400\b/g, 'hover:text-modira-cyan'],
  [/hover:border-cyan-400\/(\d+)/g, 'hover:border-modira-cyan/$1'],
  [/hover:border-emerald-400\/(\d+)/g, 'hover:border-modira-teal/$1'],
  [/group-hover:text-cyan-300\b/g, 'group-hover:text-modira-cyan'],
  [/group-hover:text-cyan-400\b/g, 'group-hover:text-modira-cyan'],
  [/hover:shadow-\[0_24px_60px_-28px_rgba\(6,182,212,0\.45\)\]/g, 'hover:shadow-[0_24px_60px_-28px_color-mix(in_srgb,var(--modira-cyan)_45%,transparent)]'],
  [/hover:shadow-\[0_24px_60px_-28px_rgba\(16,185,129,0\.45\)\]/g, 'hover:shadow-[0_24px_60px_-28px_color-mix(in_srgb,var(--modira-teal)_45%,transparent)]'],
  [/bg-white\/\[0\.02\]/g, 'bg-modira-white/[0.02]'],
  [/bg-white\/\[0\.03\]/g, 'bg-modira-white/[0.03]'],
  [/bg-white\/5\b/g, 'bg-modira-white/5'],
  [/hover:bg-white\/5\b/g, 'hover:bg-modira-white/5'],
  [/hover:bg-white\/\[0\.02\]/g, 'hover:bg-modira-white/[0.02]'],
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
  if (changed) fs.writeFileSync(file, content);
}

console.log('Landing color class migration complete.');
