#!/usr/bin/env node
/**
 * Scan frontend and landing source for off-brand colors.
 * Exit code 1 when violations are found.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.join(__dirname, '../..');

const APPROVED_HEX = new Set([
  '#147a81',
  '#0f5f66',
  '#102a43',
  '#07182b',
  '#38bdf8',
  '#f8f5ea',
  '#1f2937',
  '#ffffff',
  '#000000',
]);

const SCAN_ROOTS = [
  path.join(repoRoot, 'frontend/src'),
  path.join(repoRoot, 'landing/src'),
];

const SKIP_DIRS = new Set(['node_modules', 'dist', '.git']);

/** @type {Array<{ file: string; line: number; message: string }>} */
const violations = [];

/** @param {string} file */
function isAllowlistedLine(file, lineText) {
  const normalized = file.replace(/\\/g, '/');
  if (normalized.endsWith('CustomerProfilePanel.tsx') && /style=\{\{\s*background:/.test(lineText)) {
    return true;
  }
  if (normalized.endsWith('globals.css') || normalized.endsWith('index.css')) {
    return true;
  }
  return false;
}

/** @param {string} dir */
function walk(dir) {
  /** @type {string[]} */
  const files = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (SKIP_DIRS.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) files.push(...walk(full));
    else if (/\.(tsx?|css)$/.test(entry.name) && !/\.test\.(tsx?|ts)$/.test(entry.name)) {
      files.push(full);
    }
  }
  return files;
}

const OFF_BRAND_TAILWIND =
  /\b(slate|gray|zinc|neutral|blue|red|green|yellow|purple|pink|emerald|amber|rose|indigo|violet|orange|sky|cyan|teal)-\d+/g;

const ARBITRARY_HEX_CLASS = /(?:bg|text|border|from|via|to|ring|outline|fill|stroke)-\[#[0-9a-fA-F]{3,8}\]/g;

const HEX_PATTERN = /#([0-9a-fA-F]{3,8})\b/g;
const RGB_PATTERN = /\b(?:rgb|rgba|hsl|hsla)\(/g;

for (const root of SCAN_ROOTS) {
  if (!fs.existsSync(root)) continue;
  for (const file of walk(root)) {
    const rel = path.relative(repoRoot, file).replace(/\\/g, '/');
    const lines = fs.readFileSync(file, 'utf8').split('\n');

    lines.forEach((line, index) => {
      const lineNo = index + 1;
      if (isAllowlistedLine(rel, line)) return;

      for (const match of line.matchAll(HEX_PATTERN)) {
        const hex = match[0].toLowerCase();
        if (!APPROVED_HEX.has(hex)) {
          violations.push({ file: rel, line: lineNo, message: `Unauthorized hex ${hex}` });
        }
      }

      if (RGB_PATTERN.test(line)) {
        violations.push({ file: rel, line: lineNo, message: 'Unauthorized rgb/rgba/hsl color' });
      }

      for (const match of line.matchAll(OFF_BRAND_TAILWIND)) {
        if (match[0].startsWith('modira-')) continue;
        violations.push({ file: rel, line: lineNo, message: `Off-brand Tailwind class token "${match[0]}"` });
      }

      for (const match of line.matchAll(ARBITRARY_HEX_CLASS)) {
        violations.push({ file: rel, line: lineNo, message: `Arbitrary color class "${match[0]}"` });
      }
    });
  }
}

if (violations.length === 0) {
  console.log('Brand color audit passed.');
  process.exit(0);
}

console.error(`Brand color audit failed with ${violations.length} violation(s):\n`);
for (const v of violations) {
  console.error(`  ${v.file}:${v.line} — ${v.message}`);
}
process.exit(1);
