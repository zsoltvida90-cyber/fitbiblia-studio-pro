# BUILD BRIEF — Fit Biblia Slide/PDF TEMPLATER (code-based render engine)

> **For:** Google Antigravity (Gemini 3) IDE agent, running in zsolt's dev environment.
> **Deliverable form:** a reusable, code-based template ENGINE — NOT Canva, NOT
> Figma, NOT an interactive design editor. It ingests structured content (JSON)
> and renders branded output files to disk. No human clicks per slide.
> **Brand SSOT (read in full before writing a line of CSS):**
> `docs/fitbiblia/redesign/ART_DIRECTION_v2.md` ("Obszidián Dosszié" v2.0). This
> brief extracts the values you need; the SSOT wins on anything ambiguous here.
> **Related but DIFFERENT deliverable:** `docs/fitbiblia/redesign/ANTIGRAVITY_BUILD_SPEC.md`
> describes an interactive browser *app* (contenteditable filler). THIS brief is
> the headless, JSON-in → files-out *engine*. Reuse that spec's tokens and its
> reference HTML, but do not build a UI here.
> **Rule:** where a value is missing or a decision is unresolved, emit `TODO:` and
> stop — do not invent brand variants, fonts, colors, or copy.

---

## 1. Objective

Build a headless render engine that turns a **JSON content file** into branded
Fit Biblia visuals, pixel-identical every run, with the brand (palette, type,
grid, logo, gold treatment) hardcoded in locked templates — never regenerated,
never restyled per input. Two output families, ONE visual language:

1. **Instagram carousel** — 1080×1350 PNG, up to 15 slides per run.
2. **Lead-magnet PDF ebook** — multi-page (e.g. 30 pages) compiled PDF.

zsolt approves the design **by eye**. Marci (the reviewing agent) inspects only
the manifest, filenames, and sizes — never the raw images. So the engine must
emit a machine-checkable manifest alongside the images (see §Outputs).

## 2. Inputs

- **One JSON content file** per job: an array of slide/page objects. Each object
  carries only *content and type* (headline, body, hook-word, source, cta, niche,
  optional image path) — never styling. Schema in §Sample JSON schema.
- **Brand asset folder** (self-hosted; copy these into the engine's own
  `assets/`, do not read live repo paths at render time):

  | Asset | Copy from |
  |---|---|
  | Logo, HU transparent (RGBA) — canonical wordmark | `docs/fitbiblia/brand/fit_biblia_logo_transparent_alt.png` |
  | Gold foil texture (logo mask, screen-blend) | `web/icons/master-kit/textures/assets/gold-tile-256.png` |
  | Gold frame / CTA-bar / glass textures | `web/icons/master-kit/textures/assets/{gold-frame-rect,gold-frame-circle,cta-bar-gold,glass-panel}.png` |
  | Archivo Black + ExtraBold | `scratchpad/Archivo-Black-full.ttf`, `scratchpad/Archivo-XBold-full.ttf` |
  | Fraunces regular + italic | `scratchpad/Fraunces.ttf`, `scratchpad/Fraunces-Italic.ttf` |
  | IBM Plex Mono Medium + SemiBold | `scratchpad/IBMPlexMono-Medium.ttf`, `scratchpad/IBMPlexMono-SemiBold.ttf` |
  | Inter Regular/SemiBold/Bold | `scratchpad/Inter-{Regular,SemiBold,Bold}-full.ttf` |

  > **LOGO RULE (hard):** use the `_alt` file — it carries the Hungarian "FIT
  > BIBLIA" wordmark. The non-`_alt` transparent file reads "FIT BIBLE" (English)
  > — do NOT use it. **Never re-color, re-tint, or color-key the logo.** Place it
  > as-is; the gold in it is the real foil "crown."

- **A niche key** per slide (optional) selecting the bottom-glow accent (§Visual
  tokens → niche-glow).

## 3. Outputs

Write into a caller-specified output folder (default `output/`):

- **PNG slides:** exactly `1080×1350` px, sRGB, flat (non-transparent) background.
  Filenames zero-padded and ordered: `slideNN.png` (`slide01.png` … `slide15.png`),
  or a job-prefixed form `<job>_slideNN.png`. Render at 2× device scale
  (2160×2700) for crispness, then the final saved asset is `1080×1350`
  (downscale LANCZOS/high-quality, or render at deviceScaleFactor and let the
  headless browser emit at target — output must be exactly 1080×1350).
- **Compiled PDF:** one multi-page PDF (`<job>.pdf`) assembling the ebook pages
  in order, each page at correct aspect (A4 300dpi page, or the carousel aspect
  for a carousel-to-PDF). No blank trailing pages.
- **`manifest.json`** (Marci reviews THIS, not the images): for each output file
  emit `{ file, type, index, width, height, bytes, template, niche, hookWord,
  source? }`, plus a job summary `{ jobId, slideCount, pdfPages, generatedAt,
  allSizesOK: bool, warnings: [ ...TODO/contrast/overflow flags ] }`. Any
  auto-detectable violation (wrong dimensions, empty field, text overflow past
  safe zone) goes into `warnings`.

## 4. Tech stack & constraints

- **Rendering: browser-grade HTML/CSS via a headless browser** (Puppeteer or
  Playwright driving headless Chromium). This is the canon — the Obszidián look
  is CSS-defined (`background-clip:text` engraved gold, radial gradients,
  `feTurbulence` grain, `mix-blend-mode`). **Do NOT use Python PIL / Pillow
  compositing** — it cannot reproduce the locked look. Antigravity's dev
  environment has a real headless browser; use it.
- **PNG capture:** screenshot the rendered slide DOM at exact pixel dimensions.
  Note: the existing reference HTML bundles **snapDOM** specifically because
  `background-clip:text` (the engraved gold hook-word) rasterizes correctly with
  it and NOT with html2canvas. With Puppeteer/Playwright a full-page/element
  screenshot rasterizes `background-clip:text` natively — verify this against the
  hook-word case explicitly (§Acceptance). If it regresses, fall back to the
  snapDOM path used in the reference files.
- **PDF:** assemble multi-page via the browser's own `page.pdf()` (preferred for
  vector crispness) OR embed the rasterized per-page PNGs into a PDF (jsPDF-style).
  Either way, one compiled PDF, correct page order and aspect.
- **Self-hosted fonts only:** load the TTFs above via local `@font-face`. **No
  Google Fonts CDN `@import`** — the reference HTML uses one; strip it and ship
  local `.ttf` so renders are deterministic and offline-safe.
- **Deterministic:** same JSON in → byte-comparable images out (modulo grain
  seed; fix the grain seed). No network calls at render time.
- **Templates are locked.** The engine maps `type` → a fixed template. It never
  lets input move, resize, recolor, or restyle an element. Unknown `type` → `TODO:`
  and skip, do not improvise a layout.

## 5. Visual tokens (concrete values — quoted from the SSOT, do not deviate)

### 5.1 Canvas & grid (carousel, 1080×1350 logical px — calibrated in day1 brief)
- Content left margin `LX = 96px`; right margin `96px` (folio right-aligned to `1080−96`).
- Top safe zone `~150px`, bottom safe zone `~150px`. **No text/logo touches the canvas edge.**
- Header wordmark "FIT BIBLIA": left `x=96`, top `y≈78`.
- Header gold hairline: `x=96, y≈128, width 150px`.
- Optional faint left "ruler" line: `x≈38`, from top-150 to bottom-150, BONE at
  `26/255` alpha (very faint) + 2 short ticks.
- `TODO (reconcile):` ART_DIRECTION_v2 §5 states the *general* grid as `LX=90px`,
  top safe `78px`, bottom safe `118px`, ruler at BONE 10% opacity. The day1 brief
  re-calibrates to `LX=96 / top~150 / bottom~150` for the 1080×1350 IG frame. Use
  the **day1 (96px) values for carousel** (they are frame-calibrated); treat the
  ART_DIRECTION 90px values as the underlying 12-column module. Flag if a template
  can't satisfy both.

### 5.2 Palette (canonical HEX — exact)
| Token | HEX | RGB | Use |
|---|---|---|---|
| BONE | `#E8DFC9` | 232,223,201 | Headlines, giant number, **bold emphasis words** (the "titanium" accent) |
| MUTED_BONE | `#C7BEAB` | 199,190,171 | Subtitle, secondary text, thin/caption |
| BODY | `#D6CEBA` | 214,206,186 | Body copy base |
| GREY | `#8F8B83` (also `#96969A`) | 143,139,131 | Folio, faintest elements |
| GOLD | `#E6C15A` | 230,193,90 | **Micro-accent ONLY:** kicker text, hairline, icon outline |
| GOLD_HL | `#EFD066` | 239,208,102 | Gold highlight (hairline end, icon) |
| GOLD_DEEP | `#B8860B` | 184,134,11 | Hairline dark end (gradient) |
| Negative bordeaux | `#6E2433` (glyph edge `#9A3348`) | matte | Myth/negative side. **RED NOWHERE.** |

### 5.3 Background — warm obsidian radial (exact recipe)
```css
background: radial-gradient(120% 90% at 34% 40%,
  #100E0B 0%, #0A0908 34%, #050504 72%, #020202 100%);
/* + carbon vignette on top: */
background: radial-gradient(130% 100% at 50% 55%,
  transparent 46%, rgba(0,0,0,.55) 100%);
```
Background is ALWAYS dark, text ALWAYS light (bone). Not an option — it is the brand.

### 5.4 Film grain (mandatory)
`feTurbulence` fractalNoise, `baseFrequency 0.9`, `saturate 0`, layer `opacity ~0.05`,
`mix-blend-mode: overlay`, placed UNDER content. Fix the seed. **Shimmer/sparkle: banned.**

### 5.5 Gold — THREE separated events, NEVER mixed
- **(a) Logo foil** = real gold texture `gold-tile-256.png`, `mix-blend-mode: screen`
  on the logo only. Never elsewhere, never on the logo as a recolor.
- **(b) ONE hook-word per slide** = engraved gold, `background-clip:text`, with a
  `#2A1E07` offset `::before` rim (carved bottom edge). Font: **Fraunces 900
  italic**. Two candidate gradients are OPEN (zsolt's pick pending) — implement
  both as swappable classes `.hook--a` / `.hook--b`, default **A**:
  ```css
  /* (b/A) smooth amber ramp */
  background: linear-gradient(168deg,
    #B8860B 0%, #C8912E 20%, #E6C15A 42%, #FBF0C4 56%, #EFD066 72%, #B4801F 100%);
  -webkit-background-clip: text; background-clip: text;
  /* (b/B) fractured hammered foil — layered veins + facets + amber ramp */
  background:
    repeating-linear-gradient(27deg,  transparent 0 52px, rgba(42,30,7,.55) 52px 54px, transparent 54px 108px),
    repeating-linear-gradient(-53deg, transparent 0 68px, rgba(42,30,7,.42) 68px 69px, transparent 69px 138px),
    radial-gradient(58% 42% at 22% 24%, rgba(251,240,196,.95) 0%, transparent 60%),
    radial-gradient(52% 52% at 78% 74%, rgba(138,98,22,.9)   0%, transparent 58%),
    linear-gradient(150deg, #8A6216 0%, #C8912E 26%, #F0D583 52%, #D9A63C 74%, #8A6216 100%);
  -webkit-background-clip: text; background-clip: text;
  ```
- **(c) Verified-seal** = embossed conic medallion, footer/validation only:
  ```css
  background: conic-gradient(from 210deg,
    #8A6D18, #C9A227 25%, #E6C15A 50%, #C9A227 72%, #8A6D18); /* + inset sheen/shadow */
  ```

### 5.6 Niche-glow (bottom of frame, ≥20% height, even upward fade, `screen` blend, no hard edge)
Edzés `#FF7A1A` · Táplálkozás `#25E67A` · Mindset `#2E9BFF` · Női szemszög `#FF54A6`.
**Max ONE niche-glow event per slide.**

### 5.7 Typography (exact — no substitutions)
| Role | Font | Size @1080×1350 | Notes |
|---|---|---|---|
| Cover / closing display | **Archivo Black** | cover `~104px` / lh `118`; closing `~76px` | UPPERCASE, tracking −1.5..−2.5px, lh 0.9–0.98 |
| Inner headline | **Archivo ExtraBold** (Archivo Black fallback, slightly smaller) | `~66px` / lh `80` | |
| ONE gold hook-word | **Fraunces 900 italic** | matches its line | engraved gold (§5.5b) |
| Body | **Inter** Regular/SemiBold/Bold | `~44px` / lh `64` | |
| Kicker / section label | **IBM Plex Mono SemiBold** UPPERCASE | `~28px`, tracking +4px | gold |
| Header wordmark | **IBM Plex Mono SemiBold** UPPERCASE | `~26px`, tracking +3px | MUTED_BONE |
| Folio / page number | **IBM Plex Mono Medium** | `~24px`, tracking +2px | GREY, e.g. `02 / 06` |
| Giant ghost number (decor) | **Archivo Black** | `~430px` | bone `12/255` alpha, right-bottom bleed |

**Scale law (SSOT §4): GIANT or TINY, nothing between.** No medium sizes.
**Font gap `TODO:`** the live `store/content-factory/fonts/` folder currently ships
only Anton/Inter/Lora/Oswald. Archivo/Fraunces/IBM Plex Mono exist in `scratchpad/`
(paths in §2) — copy those into the engine's `assets/`. **Do NOT substitute Anton
for Archivo** (Anton fails the Hungarian Ő/Ű glyphs). If a required TTF is missing,
`TODO:` and stop.

### 5.8 Emphasis rule (CRITICAL — titanium, not gold)
Emphasis is by **contrast, not color**: base body is `BODY #D6CEBA` Inter Regular;
the emphasized word/clause is `BONE #E8DFC9` **Inter Bold** (lighter + heavier).
**Gold (`#E6C15A`) NEVER on body text or headlines.** Gold is micro-accent only.
Saturated/yellow gold LETTERING = forbidden (unreadable).

## 6. Slide / page types & layouts

Two modes, one system (SSOT §6). Each JSON `type` maps to a locked template:

**MODE A — MONOLIT** (scroll-stopper: cover / hook / myth):
- `cover` — logo top-center; kicker; big Archivo Black headline; gold hairline;
  subtitle; swipe hint `LAPOZZ →` (mono, gold) at bottom. Optional giant ghost number.
- `inner` — header (wordmark + hairline left, folio right e.g. `02 / 06`); kicker
  above headline (~y230); Archivo ExtraBold headline (~y300); Inter body below
  with BONE-bold emphasis; giant ghost number bottom-right.
- `myth` (myth-vs-truth split) — bordeaux `#6E2433` "myth" half vs bone/gold
  "truth" half. No red.

**MODE B — DOSSZIÉ** (credibility engine: data / source / validation / CTA):
- `data` — dark MASTHEAD bar top (`linear-gradient(#172227 → #0E1518)`) with logo
  left + monospace folio right ("DOSSZIÉ T3·01 / 09"), gold datum-hairline under
  it; center giant tabular readout (**IBM Plex Mono 600**) + a data figure
  (e.g. "1 LAW vs 12 NOISE" bar infographic). No background photo.
- `cta` / `closing` — logo top-center; kicker (`KEZDD ITT`); big closing title;
  subtitle; ONE save-CTA gold-outline pill + bookmark icon (BONE text). Exactly
  one save signal — text OR pill, not both.
- `source` — footer with a real peer-reviewed citation (monospace) + verified gold seal.

**PDF ebook pages** reuse the same templates at A4 (2480×3508 @300dpi or vector
A4 page): a cover, N inner content pages, data/dossier pages, a CTA page.
`TODO:` proof target = reproduce the existing `web/icons/a-fogyas-torvenye.pdf`
(cover + content + CTA) live via the engine — same page count and layout logic.

**Header/footer template (every inner slide S2..Sn):** wordmark + hairline top-left,
folio `NN / TT` top-right, kicker → headline → body, giant ghost number bottom-right.
The counter base is the actual slide count (`06`, not a fixed number).

## 7. Acceptance criteria (incl. NO-GO list)

**Output correctness:**
- [ ] Every PNG is exactly `1080×1350` px, sRGB, flat bg, correct zero-padded ordered filename in the output folder.
- [ ] Carousel: up to 15 slides render and export in order; PDF compiles all pages in order, correct aspect, no blank pages.
- [ ] `manifest.json` present, lists every file with type/index/width/height/bytes, and `allSizesOK:true`.
- [ ] No network request fires at render time; fonts/textures load from local `assets/` only.
- [ ] Hook-word gets the engraved gold `background-clip:text` treatment automatically and rasterizes correctly in the PNG (test this exact case).
- [ ] Consistent typography, header/folio/kicker structure, and left margin across ALL slides; safe margins respected (≥96px sides, ~150px top/bottom).
- [ ] Emphasis is BONE-bold (contrast), never colored.
- [ ] A sample run produces one demo carousel AND one demo PDF page from the sample JSON, written to `output/`.

**NO-GO list — these must NOT appear in any rendered output (SSOT §8 + day1 §5). Enforce, don't just avoid:**
- [ ] No gold "light-ray" signature (the #1 AI-tell).
- [ ] No yellow/saturated **gold lettering** anywhere (headline or body); gold = micro-accent only. No gold-on-gold / low-contrast unreadable text.
- [ ] No teal or any second accent color; gold is the sole brand accent.
- [ ] No Playfair or Anton display fonts.
- [ ] No light/paper background — always dark obsidian.
- [ ] No red anywhere; negative = matte bordeaux `#6E2433`.
- [ ] No full-word gold headline; no flat synthetic gold gradient.
- [ ] No glassmorphism, no hex-grid/HUD, no floating panels, no shimmer/sparkle.
- [ ] No two niche-glow (orange etc.) events on one page.
- [ ] No mixed word sizes inside the hook (clean hierarchy, not big/small/big).
- [ ] No large dead/empty space — content fills header-bottom to bottom-safe-zone.
- [ ] No generic stock/AI look; no random, non-meaningful icons.
- [ ] No copy rewriting — slide text is rendered verbatim from JSON; no invented hashtags/kickers where the source is empty (emit `TODO:`).

## 8. Sample JSON schema

```jsonc
{
  "jobId": "day1_carousel",
  "output": "output/day1",
  "format": "carousel",          // "carousel" (1080x1350 PNGs) | "pdf" (A4 pages) | "both"
  "hookVariant": "a",            // "a" | "b"  (global gold hook-word style, §5.5b)
  "slides": [
    {
      "type": "cover",            // cover | inner | myth | data | cta | source
      "niche": "edzes",           // edzes | taplalkozas | mindset | noi  (optional glow)
      "kicker": "MANIFESZTUM",
      "headline": "Mi a valószínűségeket mérjük.",
      "hookWord": "valószínűségeket",  // exactly ONE word → engraved gold; optional
      "subtitle": "A fitness világ tele van magabiztos ígéretekkel.",
      "swipeHint": "LAPOZZ →",
      "ghostNumber": "01"
    },
    {
      "type": "inner",
      "folio": "02 / 06",
      "kicker": "A ZAJ",
      "headline": "Marketing, nem tudomány.",
      "body": [
        { "text": "Ha valaki azt állítja, megtalálta a „tökéletes” diétát mindenkinek, az nem " },
        { "text": "tudományt árul, hanem marketinget", "emphasis": true },
        { "text": "." }
      ],
      "ghostNumber": "02"
    },
    {
      "type": "data",
      "folio": "DOSSZIÉ T3·03 / 06",
      "readout": "1 vs 12",
      "figureLabel": "1 TÖRVÉNY vs 12 ZAJ",
      "source": "Hall KD et al., Cell Metab. 2019;30(1):67-77."
    },
    {
      "type": "cta",
      "kicker": "KEZDD ITT",
      "headline": "Kezdd itt.",
      "subtitle": "Töltsd le a PDF-et a profilban.",
      "cta": "Tedd félre későbbre, és mentsd el ezt a posztot indításként!",
      "image": "assets/photos/hero_dark.jpg"   // optional; cover-cropped, brand overlay on top
    }
  ]
}
```
Field notes: `body` may be a plain string or an array of `{text, emphasis?}` runs
(emphasis → BONE Inter Bold). All user text is **escaped** before injection (no raw
HTML). Missing required field for a type → `TODO:` in warnings, skip render.

## 9. Definition of done

- Engine code committed: template CSS/HTML (ported from `web/icons/fb_template_carousel-15.html`
  and `fb_template_pdf-30p.html` — mine their CSS-variable architecture, do not
  redesign), the JSON→template binding, image cover-crop/composite, and the
  headless PNG + compiled-PDF export pipeline. Self-hosted fonts/textures in `assets/`.
- A **sample run** from a bundled sample JSON produces, in `output/`: one demo
  carousel (≥3 ordered `slideNN.png` at 1080×1350) AND one demo PDF page, plus
  `manifest.json` with `allSizesOK:true` and an empty (or only-TODO) warnings list.
- All §7 acceptance boxes pass, including the full NO-GO list and the hook-word
  rasterization test.
- No network at render time; runs headless with no per-slide human interaction.
- Any unresolved brand decision surfaced as `TODO:` (not guessed): open items are
  the hook-word gradient A/B pick, the LX 90 vs 96 grid reconciliation, and the
  PDF proof-target parity with `a-fogyas-torvenye.pdf`.
```
