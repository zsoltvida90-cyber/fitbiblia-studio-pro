# Fit Biblia — Content-JSON Schema

Companion to `fitbiblia_slide_reference.html`. The engine ingests one JSON object
per job; the template renders `slides[]` in order. Templates are LOCKED: JSON carries
content and `type` only, never styling. All text is HTML-escaped before injection.
Missing required field for a type -> engine emits `TODO:` in warnings and skips that slide.
Copy is rendered verbatim (no rewriting, no invented kickers/hashtags). No em dash in copy.

## Job object (top level)

| Field | Type | Req | Notes |
|---|---|---|---|
| `jobId` | string | yes | Job id; used for output filenames / manifest. |
| `format` | enum | yes | `carousel` (1080x1350 PNG) \| `pdf` (A4) \| `both`. |
| `hookVariant` | enum | yes | `a` (smooth amber ramp, DEFAULT) \| `b` (fractured hammered foil). Global gold hook-word style. THE open design decision. |
| `output` | string | no | Output folder (engine only; default `output/`). |
| `slides` | array | yes | Ordered slide objects (max 15 for carousel). |

## Slide object — common fields

| Field | Type | Req | Notes |
|---|---|---|---|
| `type` | enum | yes | `cover` \| `inner` \| `myth` \| `data` \| `cta`. Unknown -> TODO + skip. |
| `niche` | enum | no | `edzes` \| `taplalkozas` \| `mindset` \| `noi`. Selects the ONE bottom glow. Max one per slide. Omit = no glow. |
| `folio` | string | no | Page marker top-right, e.g. `02 / 05` or `DOSSZIÉ T3·04 / 05`. Counter base = real slide count. |
| `ghostNumber` | string | no | Giant ghost decor number (Archivo Black, bone 12/255, bottom-right bleed), e.g. `"02"`. |

## Per-type fields

### `cover` (MODE A — scroll-stopper)
| Field | Type | Req | Notes |
|---|---|---|---|
| `kicker` | string | yes | Mono uppercase gold label. |
| `headlinePre` | string | no | Text before the hook-word. |
| `hookWord` | string | no | Exactly ONE word -> engraved gold (Fraunces 900 italic). Clean hierarchy, no size-mix. |
| `headlinePost` | string | no | Text after the hook-word. |
| `subtitle` | string | yes | Muted-bone subtitle. |
| `swipeHint` | string | no | Bottom swipe cue, default `LAPOZZ →`. |

### `inner` (MODE A — content)
| Field | Type | Req | Notes |
|---|---|---|---|
| `kicker` | string | yes | Section label (keep consistent across the set). |
| `headline` | string | yes | Archivo ExtraBold headline. |
| `hookWord` | string | no | Optional ONE engraved-gold word prefixing the headline. |
| `body` | string \| run[] | yes | Plain string, OR array of `{text, emphasis?}` runs. `emphasis:true` -> BONE Inter Bold (contrast, NEVER color). |

### `myth` (MODE A — myth vs truth)
| Field | Type | Req | Notes |
|---|---|---|---|
| `kicker` | string | yes | e.g. `MÍTOSZ VS VALÓSÁG`. |
| `falseTag` | string | yes | Myth label (bordeaux edge + X glyph). RED NOWHERE. |
| `falseLine` | string | yes | The myth statement (matte muted). |
| `trueTag` | string | yes | Truth label (gold + check glyph). |
| `trueLine` | string | yes | The correction (bone). |

### `data` (MODE B — DOSSZIÉ / credibility engine)
| Field | Type | Req | Notes |
|---|---|---|---|
| `folio` | string | yes | Dossier folio in masthead, e.g. `DOSSZIÉ T3·04 / 05`. |
| `readout` | string | yes | Giant tabular readout (IBM Plex Mono 600), e.g. `1 vs 12`. |
| `figureLabel` | string | yes | Caption under the figure, e.g. `1 TÖRVÉNY vs 12 ZAJ`. |
| `source` | string | yes | Real peer-reviewed citation (mono). No background photo on this type. |
| `sealText` | string | no | Verified-seal label, default `IGAZOLT`. |

### `cta` (MODE B — closing / save)
| Field | Type | Req | Notes |
|---|---|---|---|
| `kicker` | string | yes | e.g. `KEZDD ITT`. |
| `headline` | string | yes | Closing title (Archivo Black). |
| `subtitle` | string | yes | Muted-bone subtitle. |
| `ctaLabel` | string | no | ONE save signal — gold-outline pill + bookmark, default `MENTSD EL`. Never both pill AND standalone "save" text. |
| `image` | string | no | Optional hero photo path; cover-cropped, strong dark overlay under text. |

## Body run object
`{ "text": "string", "emphasis": true|false }` — `emphasis:true` renders BONE Inter Bold.

## Hard rules (enforced, not just avoided)
- Gold = micro-accent only (kicker, hairline, hook-word, seal, icon outline). Never on body/headline lettering.
- Emphasis by contrast (BONE bold), never by color.
- Background always dark obsidian; no light/paper. No teal/second accent. No red. No Playfair/Anton. No shimmer/light-ray/glassmorphism.
- Max one niche glow per slide. One hook-word per slide. One save signal per CTA.
- No large dead space: fill header-bottom to bottom-safe-zone.
- Safe margins: sides >=96px, top/bottom ~150px.
