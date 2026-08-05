# Fit Biblia Studio Pro — Render Rewire (Option B: clean rewire to the Obszidián engine)

Date: 2026-08-05
Repo: `scratchpad/fitbiblia-studio-pro` (local working tree only — NOT committed/pushed)

## TL;DR
The export paths were rendering with the WEAK template (`templates/base_render.html`):
Google-CDN fonts (silent Arial/Times fallback when headless), a cold blue-grey
background, tiny type (60/26), no gold/texture treatment, and a **kicker/badge
that never rendered** (the template had no placeholder for it). The GOOD
"Obszidián" component system already existed (`src/templates/slide_template.js` +
`src/styles/obszidian.css`) but was only reachable from a CLI engine that was
**hard-wired to a Windows Chrome path**, so it ran on exactly one machine.

This rewire points every export path at the Obszidián engine and makes it render
headless on ANY machine (bundled Puppeteer chromium), with fonts embedded so
there is zero CDN dependency.

## What was wrong (root causes)
1. `render_engine.js` (the good engine) launched Puppeteer with
   `executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'`
   → fails to launch anywhere but that one Windows box.
2. `server.js` (`/api/generate`, `/api/export-batch`) and `batch_generator.js`
   built HTML from `base_render.html`, which:
   - `@import`s fonts from `fonts.googleapis.com` → headless render silently
     falls back to Arial/Times ("cheap look").
   - uses a cold `radial-gradient(... #16191c ...)` background instead of the
     warm obsidian gradient.
   - hard-codes small type sizes (title 60 / body 26 vs. the engine's 90 / 38).
   - computes a `badge-clean` element but the template has **no `{{BADGE}}`
     placeholder and no `.badge-clean` CSS** → the kicker/badge silently vanishes.
3. The good `obszidian.css` used `@font-face` with **relative** file paths, which
   do not resolve under Puppeteer `setContent()` (no base URL) → even the good
   engine risked font fallback in some load modes.

## What I changed (file by file)

### NEW: `src/render_page.js`
Single source of truth for portable rendering. Exports:
- `launchBrowser()` — headless Puppeteer with cross-platform executable
  resolution: honours `PUPPETEER_EXECUTABLE_PATH` / `CHROME_PATH` if set,
  otherwise uses Puppeteer's **bundled chromium** (no hard-coded path).
- `getObsidianInlineStyle()` — reads `obszidian.css`, strips its relative-path
  `@font-face` rules, and prepends `@font-face` rules with the TTFs embedded as
  **base64 `data:` URIs** (Archivo Black, Archivo ExtraBold, Fraunces, IBM Plex
  Mono, Inter). Cached after first build.
- `buildSelfContainedDocument(slide, opts)` — returns a fully self-contained HTML
  document (CSS + fonts inlined, no external refs) → renders identically via
  `setContent()` on any origin, no CDN, no Arial fallback.
- `mapWebSlideToEngine(webSlide)` — translates the web-UI slide shape
  (`{type, badge, headline, hookWord, body, icon}`) into the engine's richer
  shape (`headerLeft`/kicker, badge, hookWord, stats, niche, …). Notably it
  routes `badge` → `headerLeft` so the **kicker/badge renders again**, and turns
  a `stat` slide's `hookWord` (e.g. "-500 kcal") into the engine's gold
  `stat-number` component so the headline number is not lost.

### `src/templates/slide_template.js`
- `generateSlideHTML()` now accepts `options.inlineStyle`. When present it emits
  a self-contained `<style>…</style>` (fonts + CSS) instead of the relative
  `<link href="../src/styles/obszidian.css">`. Legacy `<link>` behaviour is kept
  as the default (backward compatible).

### `src/render_engine.js` (CLI batch engine)
- Removed the hard-coded Windows Chrome `executablePath`; now uses
  `launchBrowser()`.
- Replaced the temp-HTML-file + `file:///` navigation dance with
  `page.setContent(buildSelfContainedDocument(...), { waitUntil: 'load' })`.
  (`networkidle0` was wrong for a no-network self-contained doc and timed out;
  `load` is correct.)
- Removed the now-unnecessary `temp_slides/` directory handling.

### `server.js` (web app — the export path)
- `/api/generate` and `/api/export-batch`: replaced the whole
  `base_render.html` placeholder-injection block (and the per-slide
  `contentBlock` switch) with
  `buildSelfContainedDocument(mapWebSlideToEngine(slide), {docTitle, pageIndex, totalPages})`.
- Both routes now launch via `launchBrowser()` (bundled chromium) instead of an
  inline `puppeteer.launch`.
- Dropped the dead `puppeteer` import and the dead `base_render.html` reads.

### `batch_generator.js` (30-day master batch export)
- Same rewire: `launchBrowser()` + `buildSelfContainedDocument(mapWebSlideToEngine(...))`.
- Removed the throwaway Express asset server on :3001 (self-contained docs need
  no served assets) and its `server.close()` calls.

## Verification (headless, on this Linux/WSL box, no images read into context)
- `npm install` pulled Puppeteer's bundled chromium
  (`~/.cache/puppeteer/chrome/linux-148.0.7778.97`).
- CLI: `node src/render_engine.js --input sample_input.json` →
  `output/slide01..04.png` at **2160×2700** (1080×1350 @2×), ~1.8–2.3 MB each,
  plus a valid **4-page** `day1_demo.pdf`.
- Headless probe (computed styles, no pixels read): **8 local fonts loaded**,
  `fonts.googleapis.com` absent, `document.fonts.check("900 90px 'Archivo Black'")`,
  Inter and Fraunces all **true**; headline computed font = `Archivo Black` at
  **90px**; `.slide-canvas` background = warm obsidian
  `radial-gradient(... rgb(16,14,11) ...)` (not the cold blue-grey).
- Web: `POST /api/generate` (carousel, 4 web-shaped slides) → **HTTP 200**, valid
  PDF, **4 pages at exactly 1080×1350**.

## Known limitation / decision needed (NOT introduced by this rewire)
- **ZIP export (`/api/export-batch`) is broken by a dependency bug.**
  `package.json` pins `archiver@^8.0.0`; the installed `archiver@8.0.0` exports
  only classes (`Archiver`, `ZipArchive`, …) — **no callable `archiver('zip', …)`
  factory and no default export** — so the route throws "archiver is not a
  function". The real `archiver` npm package tops out around v7 with the classic
  factory, so `8.0.0` looks like a wrong/suspect pin. This was already broken in
  the Initial commit and is independent of the render change. I left the import
  as-is (so the server still boots and `/api/generate` works) and flagged it.
  **Decision for zsolt:** repin to `archiver@^7` (then `archiver('zip', …)` works
  as written) or rewrite the route against the installed class API. PNG/PDF
  export is unaffected.
- The Obszidián canvas is natively **1080×1350** (carousel). `story` (1080×1920)
  and `pdf` (1240×1754) formats will render the 1080×1350 canvas inside the
  larger viewport rather than filling it. Carousel (the default and primary
  format) is pixel-perfect. Adapting the design to other aspect ratios is a
  design task, out of scope for "wire in, don't redesign".

## How the Antigravity dev applies this on the moneymaker machine
1. Copy the source changes:
   ```
   cd <repo>
   git apply /path/to/fitbiblia-rewire.patch      # patch covers the 5 source files
   ```
   (The patch includes the new file `src/render_page.js` in full.)
2. Ensure the local fonts exist at `assets/fonts/` (already present in the repo):
   Archivo-Black.ttf, Archivo-ExtraBold.ttf, Fraunces-900Italic.ttf,
   IBMPlexMono-Medium.ttf, IBMPlexMono-SemiBold.ttf, Inter-Regular.ttf,
   Inter-SemiBold.ttf, Inter-Bold.ttf.
3. `npm install` (pulls Puppeteer's bundled chromium — no system Chrome needed).
4. Smoke test:
   ```
   node src/render_engine.js --input sample_input.json
   # -> output/slide01..NN.png (2160x2700) + <jobId>.pdf
   npm start   # then POST /api/generate -> premium PDF
   ```
5. Optional: to force a specific Chrome instead of bundled chromium, set
   `PUPPETEER_EXECUTABLE_PATH=/path/to/chrome` (or `CHROME_PATH`). No code edit
   needed — the Windows hard-coded path is gone.
6. If ZIP export is required, first resolve the `archiver` dependency (see above).

## Leftover / harmless
- `templates/base_render.html` and `src/templates/base_render.html` are no longer
  used by any export path but were left in place (unused, safe to delete later).
- `getIconHtml` / `getSwipeArrowHtml` in `server.js` and `batch_generator.js` are
  now unused (harmless). The Obszidián engine handles its own iconography/motion
  cues; kept to minimise churn.
