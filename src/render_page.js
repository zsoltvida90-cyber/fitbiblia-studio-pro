// Shared, cross-platform render helpers for the Fit Biblia "Obszidián" engine.
//
// This module is the single source of truth for:
//   1. Launching a headless Chromium that works on ANY machine
//      (bundled Puppeteer chromium by default; env-overridable path).
//   2. Producing a FULLY SELF-CONTAINED slide document: the Obszidián CSS is
//      inlined and every font is embedded as a base64 data: URI, so the page
//      renders identically whether loaded via file://, http:// or setContent(),
//      with NO Google-CDN dependency and NO silent Arial/Times fallback.
//
// Both the CLI batch engine (render_engine.js) and the web export routes
// (server.js) go through here, so there is exactly one premium look.

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import puppeteer from 'puppeteer';
import { generateSlideHTML } from './templates/slide_template.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '..');
const FONTS_DIR = path.join(REPO_ROOT, 'assets', 'fonts');
const OBSZIDIAN_CSS = path.join(REPO_ROOT, 'src', 'styles', 'obszidian.css');

// Local font files -> @font-face descriptors. Family names MUST match the ones
// referenced in obszidian.css (Archivo Black / Archivo ExtraBold / Fraunces /
// IBM Plex Mono / Inter).
const FONT_FACES = [
  { file: 'Archivo-Black.ttf', family: 'Archivo Black', weight: 900, style: 'normal' },
  { file: 'Archivo-ExtraBold.ttf', family: 'Archivo ExtraBold', weight: 800, style: 'normal' },
  { file: 'Fraunces-900Italic.ttf', family: 'Fraunces', weight: 900, style: 'italic' },
  { file: 'IBMPlexMono-Medium.ttf', family: 'IBM Plex Mono', weight: 500, style: 'normal' },
  { file: 'IBMPlexMono-SemiBold.ttf', family: 'IBM Plex Mono', weight: 600, style: 'normal' },
  { file: 'Inter-Regular.ttf', family: 'Inter', weight: 400, style: 'normal' },
  { file: 'Inter-SemiBold.ttf', family: 'Inter', weight: 600, style: 'normal' },
  { file: 'Inter-Bold.ttf', family: 'Inter', weight: 700, style: 'normal' }
];

let _styleCache = null;

/**
 * Build the @font-face block with base64-embedded TTFs.
 */
function buildEmbeddedFontFaceCss() {
  return FONT_FACES.map(({ file, family, weight, style }) => {
    const abs = path.join(FONTS_DIR, file);
    if (!fs.existsSync(abs)) {
      throw new Error(`Required font missing: ${abs}`);
    }
    const b64 = fs.readFileSync(abs).toString('base64');
    return `@font-face {
  font-family: '${family}';
  src: url('data:font/ttf;base64,${b64}') format('truetype');
  font-weight: ${weight};
  font-style: ${style};
  font-display: block;
}`;
  }).join('\n');
}

/**
 * Return the complete inline stylesheet: embedded fonts + Obszidián CSS with its
 * own (relative-path) @font-face rules stripped out. Cached after first build.
 */
export function getObsidianInlineStyle() {
  if (_styleCache) return _styleCache;
  const rawCss = fs.readFileSync(OBSZIDIAN_CSS, 'utf-8');
  // Drop the original @font-face rules (they use relative paths that do not
  // resolve under setContent()); the embedded ones above replace them.
  const cssWithoutFontFaces = rawCss.replace(/@font-face\s*\{[^}]*\}/g, '').trimStart();
  _styleCache = `${buildEmbeddedFontFaceCss()}\n\n${cssWithoutFontFaces}`;
  return _styleCache;
}

/**
 * Build a fully self-contained HTML document for a single slide.
 * No external CSS, no external fonts, no CDN. Renders anywhere.
 */
export function buildSelfContainedDocument(slide, options = {}) {
  return generateSlideHTML(slide, { ...options, inlineStyle: getObsidianInlineStyle() });
}

/**
 * Cross-platform Chromium executable resolution.
 * - Honour PUPPETEER_EXECUTABLE_PATH / CHROME_PATH if the operator sets one.
 * - Otherwise return undefined so Puppeteer uses its own bundled chromium,
 *   which works headless on Linux/WSL/macOS/Windows without any hard-coded path.
 */
export function resolveExecutablePath() {
  const envPath = process.env.PUPPETEER_EXECUTABLE_PATH || process.env.CHROME_PATH;
  if (envPath && fs.existsSync(envPath)) return envPath;
  return undefined; // -> Puppeteer bundled chromium
}

/**
 * Launch a headless browser with sane, portable defaults.
 */
export async function launchBrowser(extraArgs = []) {
  const executablePath = resolveExecutablePath();
  const launchOpts = {
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--allow-file-access-from-files',
      ...extraArgs
    ]
  };
  if (executablePath) launchOpts.executablePath = executablePath;
  return puppeteer.launch(launchOpts);
}

/**
 * Map a web-UI slide object (from public/index.html / the /api routes) onto the
 * richer Obszidián engine slide shape consumed by generateSlideHTML().
 *
 * The web UI speaks: { type, badge, headline, hookWord, body(string), icon }.
 * The engine speaks: headerLeft (kicker), headline, hookWord, body, stats, etc.
 */
export function mapWebSlideToEngine(webSlide = {}) {
  const type = webSlide.type || webSlide.slideType || 'cover';
  const badge = (webSlide.badge || webSlide.headerLeft || '').trim();
  const headline = webSlide.headline || webSlide.title || '';
  const hookWord = webSlide.hookWord || webSlide.hook || '';
  const bodyRaw = webSlide.body;
  const body = typeof bodyRaw === 'string'
    ? bodyRaw
    : (Array.isArray(bodyRaw) ? bodyRaw.map(b => b.text || '').join('') : '');

  const engine = {
    type,
    headline,
    hookWord,
    body,
    // Kicker / header-left label. On cover the engine also renders this as the
    // gold pill badge, so it is never silently dropped again.
    headerLeft: badge || undefined,
    badge: badge || undefined,
    niche: webSlide.niche || undefined,
    subtitle: webSlide.subtitle || undefined,
    ctaText: webSlide.ctaText || webSlide.cta || undefined
  };

  // 'stat' slides carry the headline number in hookWord ("-500 kcal"); surface
  // it through the engine's gold stat-number component instead of losing it.
  if (type === 'stat' && hookWord && !Array.isArray(webSlide.stats)) {
    engine.stats = [{ number: hookWord, label: badge || '' }];
  } else if (Array.isArray(webSlide.stats)) {
    engine.stats = webSlide.stats;
  }

  return engine;
}
