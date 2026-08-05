import express from 'express';
import cors from 'cors';
import path from 'path';
import fs from 'fs';
import puppeteer from 'puppeteer';
import { PDFDocument } from 'pdf-lib';
import sqlite3 from 'sqlite3';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const archiver = require('archiver');

const dbPath = path.resolve('projects.db');
const db = new sqlite3.Database(dbPath, (err) => {
  if (err) {
    console.error('Error opening database', err.message);
  } else {
    db.run(`CREATE TABLE IF NOT EXISTS projects (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      deck_json TEXT NOT NULL,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )`);
  }
});

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.static(path.resolve('public')));
app.use('/assets', express.static(path.resolve('assets')));

// Helper: Format dimensions map
function getCanvasDimensions(canvasFormat) {
  switch (canvasFormat) {
    case 'story':
      return { width: 1080, height: 1920 };
    case 'pdf':
      return { width: 1240, height: 1754 }; // A4 aspect at High DPI
    case 'carousel':
    default:
      return { width: 1080, height: 1350 };
  }
}

// Icon SVG helper map (Lucide icons - 64x64 with brand drop-shadow)
function getIconHtml(iconName, accentColor) {
  if (!iconName || iconName === 'none') return '';
  const color = accentColor || '#E6C15A';
  const styleAttr = `class="icon-box"`;

  const icons = {
    flame: `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" ${styleAttr}><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>`,
    target: `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" ${styleAttr}><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>`,
    brain: `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" ${styleAttr}><path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/><path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/><path d="M12 5v13"/></svg>`,
    book: `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" ${styleAttr}><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-0.5-5Z"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>`,
    check: `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" ${styleAttr}><path d="M20 6 9 17l-5-5"/></svg>`,
    alert: `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" ${styleAttr}><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>`
  };

  return icons[iconName] || '';
}

// Swipe Arrow HTML helper (positioned lower at bottom 15%)
function getSwipeArrowHtml(slideType, accentColor) {
  if (slideType === 'cover' || slideType === 'cta') return '';
  const color = accentColor || '#E6C15A';
  return `
    <div class="swipe-arrow" style="position: absolute; right: 40px; bottom: 15%; color: var(--accent); opacity: 0.6; z-index: 10;">
      <svg width="40" height="60" viewBox="0 0 24 40" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="8 12 16 20 8 28"></polyline>
      </svg>
    </div>
  `;
}

// API Route: POST /api/parse-ai (Real AI Integration Shell)
app.post('/api/parse-ai', (req, res) => {
  try {
    const { text } = req.body;
    
    // AI Mock response returning strict JSON array representing parsed slides
    const mockSlides = [
      {
        type: 'cover',
        badge: '',
        headline: 'A FOGYÁS TÖRVÉNYE',
        hookWord: 'törvénye',
        body: 'A zsírégetés alaptörvénye a tartós kalóriadeficit. A szervezet kizárólag hiány esetén bont zsírt.',
        icon: 'flame',
        offsetY: 0,
        contentWidth: 888
      },
      {
        type: 'inner',
        badge: '01. FEJEZET',
        headline: 'Energiamérleg Szabálya',
        hookWord: '',
        body: 'Az energiaegyenleg szabályozza a testtömeg változását. Függetlenül a diéta típusától, a zsírégetés alaptörvénye a tartós kalóriadeficit.',
        icon: 'book',
        offsetY: 0,
        contentWidth: 888
      },
      {
        type: 'stat',
        badge: '02. STATISZTIKA',
        headline: 'OPTIMÁLIS DEFICIT',
        hookWord: '-500 kcal',
        body: 'A fenntartható zsívesztés tudományosan igazolt aranyszabálya.',
        icon: 'target',
        offsetY: 0,
        contentWidth: 888
      },
      {
        type: 'cta',
        badge: 'KÖVESS MINKET',
        headline: 'MENTS EL EZT A POSZTOT',
        hookWord: '',
        body: 'Napi bizonyíték-alapú fitnesz és táplálkozási tartalmak a profilon található linken.',
        icon: 'check',
        offsetY: 0,
        contentWidth: 888
      }
    ];

    res.json({ slides: mockSlides });
  } catch (err) {
    console.error('AI Parsing error:', err);
    res.status(500).json({ error: 'AI feldolgozás sikertelen' });
  }
});


// API Route: GET /api/projects
app.get('/api/projects', (req, res) => {
  db.all('SELECT id, name, updated_at FROM projects ORDER BY updated_at DESC', [], (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json({ projects: rows });
  });
});

// API Route: GET /api/projects/:id
app.get('/api/projects/:id', (req, res) => {
  db.get('SELECT * FROM projects WHERE id = ?', [req.params.id], (err, row) => {
    if (err) return res.status(500).json({ error: err.message });
    if (!row) return res.status(404).json({ error: 'Project not found' });
    try {
      row.deck = JSON.parse(row.deck_json);
      delete row.deck_json;
      res.json(row);
    } catch (e) {
      res.status(500).json({ error: 'Failed to parse project data' });
    }
  });
});

// API Route: POST /api/projects
app.post('/api/projects', (req, res) => {
  const { name, deck } = req.body;
  if (!name || !deck) return res.status(400).json({ error: 'Name and deck are required' });
  
  const deckJson = JSON.stringify(deck);
  db.run('INSERT INTO projects (name, deck_json, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)', [name, deckJson], function(err) {
    if (err) return res.status(500).json({ error: err.message });
    res.json({ id: this.lastID, name, message: 'Project saved successfully' });
  });
});

// API Route: POST /api/parse-text (Regex Fallback Endpoint)
app.post('/api/parse-text', (req, res) => {
  try {
    const { text } = req.body;
    if (!text || text.trim() === '') {
      return res.status(400).json({ error: 'Nincs megadva feldolgozandó szöveg' });
    }

    const blocks = text.split(/(?=(?:S\d+(?:[^\:]*?)\:|CTA\:|CAPTION\:))/gi).filter(b => b.trim() !== '');
    const slides = [];

    blocks.forEach((block, index) => {
      if (block.match(/^CAPTION\:/i)) return; 

      let layout = 'inner';
      let cleanText = block.replace(/^(S\d+(?:[^\:]*?)\:|CTA\:)/i, '').trim();
      
      if (block.match(/^S1\:/i)) {
        layout = 'cover';
      } else if (block.match(/^S\d+\s*\(adat/i)) {
        layout = 'stat';
      } else if (block.match(/^CTA\:/i)) {
        layout = 'cta';
      }

      const lines = cleanText.split('\n').map(l => l.trim()).filter(Boolean);
      let titleVal = lines[0] || (layout === 'cover' ? 'GENERÁLT FŐCÍM' : 'DIACÍM');
      let bodyVal = lines.length > 1 ? lines.slice(1).join('\n') : cleanText;
      let hookVal = '';

      if (layout === 'cover') {
        hookVal = titleVal.split(' ').pop().toLowerCase();
      } else if (layout === 'stat') {
        const nums = cleanText.match(/[-+]?\d[\d.,]*/g);
        hookVal = nums ? nums[0] : '-500 kcal';
      }

      slides.push({
        type: layout,
        badge: layout === 'cover' ? '' : (layout === 'cta' ? 'KÖVESS MINKET' : `0${index + 1}. SLIDE`),
        headline: titleVal.toUpperCase(),
        hookWord: hookVal, 
        body: bodyVal,
        icon: layout === 'cover' ? 'flame' : (layout === 'stat' ? 'target' : (layout === 'cta' ? 'check' : 'book')),
        offsetY: 0,
        contentWidth: 888
      });
    });

    res.json({ slides });
  } catch (err) {
    console.error('Text parsing error:', err);
    res.status(500).json({ error: 'Hiba a szöveg feldolgozása során' });
  }
});

// API Route: POST /api/generate
app.post('/api/generate', async (req, res) => {
  let browser;
  let page;
  try {
    const { format, slides, slide, nicheColor, bgColor, accentColor, showLogo, logoSize: rawLogoSize, titleSize: rawTitleSize, bodySize: rawBodySize } = req.body;
    
    const slideDeck = Array.isArray(slides) ? slides : [slide || req.body];
    const canvasFormat = format || 'carousel';
    const dimensions = getCanvasDimensions(canvasFormat);

    const customBg = bgColor || '#0C0D0E';
    const customAccent = accentColor || '#E6C15A';
    const displayLogo = (showLogo === false) ? 'none' : 'block';
    const logoSize = parseInt(rawLogoSize || 80, 10);
    const globalTitleSize = parseInt(rawTitleSize || 60, 10);
    const globalBodySize = parseInt(rawBodySize || 26, 10);

    let ambientColor = '#25E67A'; // Default Green
    const nicheInput = (nicheColor || '').toLowerCase();
    if (nicheInput.includes('edzes') || nicheInput.includes('orange') || nicheInput === '#ff7a1a') {
      ambientColor = '#FF7A1A';
    } else if (nicheInput.includes('mindset') || nicheInput.includes('blue') || nicheInput === '#2e9bff') {
      ambientColor = '#2E9BFF';
    } else if (nicheInput.startsWith('#')) {
      ambientColor = nicheInput;
    }

    const tempDir = path.resolve('temp_web');
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    const baseTemplatePath = path.resolve('templates/base_render.html');
    const templateStr = fs.readFileSync(baseTemplatePath, 'utf-8');

      browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--allow-file-access-from-files']
      });

      page = await browser.newPage();
      await page.setViewport({ width: dimensions.width, height: dimensions.height, deviceScaleFactor: 2 });

      const pdfDoc = await PDFDocument.create();
      const timestamp = Date.now();

    for (let i = 0; i < slideDeck.length; i++) {
      const currentSlide = slideDeck[i];
      const slideType = currentSlide.type || currentSlide.slideType || 'cover';
      const badgeVal = (currentSlide.badge || currentSlide.headerLeft || '').trim();
      const titleVal = currentSlide.headline || currentSlide.title || 'A FOGYÁS TÖRVÉNYE';
      const hookVal = (currentSlide.hookWord || currentSlide.hook || '').toLowerCase();
      const bodyVal = typeof currentSlide.body === 'string' ? currentSlide.body : (Array.isArray(currentSlide.body) ? currentSlide.body.map(b => b.text || '').join('') : '');
      const iconHtml = getIconHtml(currentSlide.icon, customAccent);
      const swipeArrowHtml = getSwipeArrowHtml(slideType, customAccent);
      const titleSize = currentSlide.titleSize || globalTitleSize;
      const bodySize = currentSlide.bodySize || globalBodySize;
      const offsetY = parseInt(currentSlide.offsetY || 0, 10);
      const contentWidth = parseInt(currentSlide.contentWidth || 888, 10);

      // Optional Badge HTML
      const badgeHtml = badgeVal ? `<div class="badge-clean">${badgeVal}</div>` : `<div></div>`;

      // 3D Background Watermark Pagination Number (empty for cover, 2, 3, 4 for others)
      const watermarkNum = (slideType === 'cover') ? '' : String(i + 1);

      // Construct Content Block with dynamic typography scaling
      let contentBlock = '';
      switch (slideType) {
        case 'cta':
          contentBlock = `
            <div class="title-main" >${titleVal}</div>
            <div class="body-text" style="margin-top: 20px;">${bodyVal}</div>
            <div class="ig-action-bar">
              <div>[ ♥ LIKE ]</div>
              <div>[ 💬 COMMENT ]</div>
              <div>[ ✈ SHARE ]</div>
              <div>[ 💾 SAVE ]</div>
            </div>
          `;
          break;

        case 'inner':
          contentBlock = `
            <div class="body-text" style="font-family: 'Archivo', sans-serif; color: #E8DFC9; text-transform: uppercase; margin-bottom: 20px; font-size: var(--title-size);">${titleVal}</div>
            <div class="body-text" >${bodyVal}</div>
          `;
          break;

        case 'myth':
          contentBlock = `
            <div style="background: rgba(110, 36, 51, 0.15); border: 1px solid rgba(110, 36, 51, 0.5); padding: 32px; border-radius: 12px; margin-bottom: 20px;">
              <div style="font-family: 'IBM Plex Mono', monospace; color: #FF54A6; font-weight: 600; margin-bottom: 12px; font-size: 18px; letter-spacing: 1.5px;">TÉVHIT / MÍTOSZ</div>
              <div class="body-text" style="font-size: var(--title-size);">${titleVal}</div>
            </div>
            <div style="background: rgba(37, 230, 122, 0.08); border: 1px solid rgba(37, 230, 122, 0.4); padding: 32px; border-radius: 12px;">
              <div style="font-family: 'IBM Plex Mono', monospace; color: #25E67A; font-weight: 600; margin-bottom: 12px; font-size: 18px; letter-spacing: 1.5px;">VALÓSÁG / TUDOMÁNY</div>
              <div class="body-text" >${bodyVal}</div>
            </div>
          `;
          break;

        case 'stat':
          contentBlock = `
            <div class="body-text" style="font-family: 'Archivo', sans-serif; font-size: var(--title-size); font-weight: 800; color: #E8DFC9; text-transform: uppercase;">${titleVal}</div>
            <div style="font-family: 'Archivo', sans-serif; font-size: 110px; font-weight: 900; color: var(--accent); line-height: 1; margin: 20px 0;">${hookVal}</div>
            <div class="body-text" >${bodyVal}</div>
          `;
          break;

        case 'cover':
        default:
          contentBlock = `
            <div class="title-main" style="font-size: var(--title-size);">${titleVal}</div>
            <div class="hook-word">${hookVal}</div>
            <div class="body-text" >${bodyVal}</div>
          `;
          break;
      }

      const injectedHtml = templateStr
        .replace(/\{\{WIDTH\}\}/g, dimensions.width)
        .replace(/\{\{HEIGHT\}\}/g, dimensions.height)
        .replace(/\{\{BADGE_HTML\}\}/g, badgeHtml)
        .replace(/\{\{WATERMARK_NUMBER\}\}/g, watermarkNum)
        .replace(/\{\{SWIPE_ARROW_HTML\}\}/g, swipeArrowHtml)
        .replace(/\{\{BG_COLOR\}\}/g, customBg)
        .replace(/\{\{ACCENT_COLOR\}\}/g, customAccent)
        .replace(/\{\{LOGO_DISPLAY\}\}/g, displayLogo)
        .replace(/\{\{LOGO_SIZE\}\}/g, logoSize)
        .replace(/\{\{NICHE_COLOR\}\}/g, ambientColor)
        .replace(/\{\{OFFSET_Y\}\}/g, offsetY)
        .replace(/\{\{CONTENT_WIDTH\}\}/g, contentWidth)
        .replace(/\{\{TITLE_SIZE\}\}/g, titleSize)
        .replace(/\{\{BODY_SIZE\}\}/g, bodySize)
        .replace(/\{\{ICON_HTML\}\}/g, iconHtml)
        .replace(/\{\{CONTENT_BLOCK\}\}/g, contentBlock);

      await page.setContent(injectedHtml, { waitUntil: 'networkidle0', url: 'http://localhost:3000' });
      await page.evaluateHandle(() => document.fonts.ready); // CRITICAL: Wait for Google Fonts!
      await page.evaluateHandle(() => Promise.all(Array.from(document.images).filter(img => !img.complete).map(img => new Promise(resolve => { img.onload = img.onerror = resolve; }))));

      const slidePngPath = path.join(tempDir, `slide_${i}_${timestamp}.png`);
      await page.screenshot({ path: slidePngPath, clip: { x: 0, y: 0, width: dimensions.width, height: dimensions.height } });

      const pngBytes = fs.readFileSync(slidePngPath);
      const pngImage = await pdfDoc.embedPng(pngBytes);
      const pdfPage = pdfDoc.addPage([dimensions.width, dimensions.height]);
      pdfPage.drawImage(pngImage, { x: 0, y: 0, width: dimensions.width, height: dimensions.height });

      fs.rmSync(slidePngPath, { force: true });
    }

    const pdfPath = path.join(tempDir, `output_deck_${timestamp}.pdf`);
    const pdfBytes = await pdfDoc.save();
    fs.writeFileSync(pdfPath, pdfBytes);

    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', `attachment; filename="fit_biblia_studio_pro_${timestamp}.pdf"`);
    return res.sendFile(pdfPath, () => {
      fs.rmSync(pdfPath, { force: true });
    });

  } catch (error) {
    console.error('Error generating slide deck:', error);
    res.status(500).json({ error: 'Failed to generate slide deck', details: error.message });
  } finally {
    if (page) await page.close().catch(e => console.error(e));
    if (browser) await browser.close().catch(e => console.error(e));
  }
});


// API Route: POST /api/export-batch
app.post('/api/export-batch', async (req, res) => {
  let browser;
  let page;
  try {
    const { format, slides, slide, nicheColor, bgColor, accentColor, showLogo, logoSize: rawLogoSize, titleSize: rawTitleSize, bodySize: rawBodySize } = req.body;
    
    const slideDeck = Array.isArray(slides) ? slides : [slide || req.body];
    const canvasFormat = format || 'carousel';
    const dimensions = getCanvasDimensions(canvasFormat);

    const customBg = bgColor || '#0C0D0E';
    const customAccent = accentColor || '#E6C15A';
    const displayLogo = (showLogo === false) ? 'none' : 'block';
    const logoSize = parseInt(rawLogoSize || 80, 10);
    const globalTitleSize = parseInt(rawTitleSize || 60, 10);
    const globalBodySize = parseInt(rawBodySize || 26, 10);

    let ambientColor = '#25E67A'; // Default Green
    const nicheInput = (nicheColor || '').toLowerCase();
    if (nicheInput.includes('edzes') || nicheInput.includes('orange') || nicheInput === '#ff7a1a') {
      ambientColor = '#FF7A1A';
    } else if (nicheInput.includes('mindset') || nicheInput.includes('blue') || nicheInput === '#2e9bff') {
      ambientColor = '#2E9BFF';
    } else if (nicheInput.startsWith('#')) {
      ambientColor = nicheInput;
    }

    const tempDir = path.resolve('temp_web');
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    const baseTemplatePath = path.resolve('templates/base_render.html');
    const templateStr = fs.readFileSync(baseTemplatePath, 'utf-8');

    browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--allow-file-access-from-files']
    });

    page = await browser.newPage();
    await page.setViewport({ width: dimensions.width, height: dimensions.height, deviceScaleFactor: 2 });

    const timestamp = Date.now();
    const zipPath = path.join(tempDir, `export_deck_${timestamp}.zip`);
    const output = fs.createWriteStream(zipPath);
    const archive = archiver('zip', { zlib: { level: 9 } });

    // Wait for the archive to finish writing to disk
    const archivePromise = new Promise((resolve, reject) => {
      output.on('close', resolve);
      archive.on('error', reject);
    });

    archive.pipe(output);

    for (let i = 0; i < slideDeck.length; i++) {
      const currentSlide = slideDeck[i];
      const slideType = currentSlide.type || currentSlide.slideType || 'cover';
      const badgeVal = (currentSlide.badge || currentSlide.headerLeft || '').trim();
      const titleVal = currentSlide.headline || currentSlide.title || 'A FOGYÁS TÖRVÉNYE';
      const hookVal = (currentSlide.hookWord || currentSlide.hook || '').toLowerCase();
      const bodyVal = typeof currentSlide.body === 'string' ? currentSlide.body : (Array.isArray(currentSlide.body) ? currentSlide.body.map(b => b.text || '').join('') : '');
      const iconHtml = getIconHtml(currentSlide.icon, customAccent);
      const swipeArrowHtml = getSwipeArrowHtml(slideType, customAccent);
      const titleSize = currentSlide.titleSize || globalTitleSize;
      const bodySize = currentSlide.bodySize || globalBodySize;
      const offsetY = parseInt(currentSlide.offsetY || 0, 10);
      const contentWidth = parseInt(currentSlide.contentWidth || 888, 10);

      const badgeHtml = badgeVal ? `<div class="badge-clean">${badgeVal}</div>` : `<div></div>`;
      const watermarkNum = (slideType === 'cover') ? '' : String(i + 1);

      let contentBlock = '';
      switch (slideType) {
        case 'cta':
          contentBlock = `
            <div class="title-main" >${titleVal}</div>
            <div class="body-text" style="margin-top: 20px;">${bodyVal}</div>
            <div class="ig-action-bar">
              <div>[ ♥ LIKE ]</div>
              <div>[ 💬 COMMENT ]</div>
              <div>[ ✈ SHARE ]</div>
              <div>[ 💾 SAVE ]</div>
            </div>
          `;
          break;
        case 'inner':
          contentBlock = `
            <div class="body-text" style="font-family: 'Archivo', sans-serif; color: #E8DFC9; text-transform: uppercase; margin-bottom: 20px; font-size: var(--title-size);">${titleVal}</div>
            <div class="body-text" >${bodyVal}</div>
          `;
          break;
        case 'myth':
          contentBlock = `
            <div style="background: rgba(110, 36, 51, 0.15); border: 1px solid rgba(110, 36, 51, 0.5); padding: 32px; border-radius: 12px; margin-bottom: 20px;">
              <div style="font-family: 'IBM Plex Mono', monospace; color: #FF54A6; font-weight: 600; margin-bottom: 12px; font-size: 18px; letter-spacing: 1.5px;">TÉVHIT / MÍTOSZ</div>
              <div class="body-text" style="font-size: var(--title-size);">${titleVal}</div>
            </div>
            <div style="background: rgba(37, 230, 122, 0.08); border: 1px solid rgba(37, 230, 122, 0.4); padding: 32px; border-radius: 12px;">
              <div style="font-family: 'IBM Plex Mono', monospace; color: #25E67A; font-weight: 600; margin-bottom: 12px; font-size: 18px; letter-spacing: 1.5px;">VALÓSÁG / TUDOMÁNY</div>
              <div class="body-text" >${bodyVal}</div>
            </div>
          `;
          break;
        case 'stat':
          contentBlock = `
            <div class="body-text" style="font-family: 'Archivo', sans-serif; font-size: var(--title-size); font-weight: 800; color: #E8DFC9; text-transform: uppercase;">${titleVal}</div>
            <div style="font-family: 'Archivo', sans-serif; font-size: 110px; font-weight: 900; color: var(--accent); line-height: 1; margin: 20px 0;">${hookVal}</div>
            <div class="body-text" >${bodyVal}</div>
          `;
          break;
        case 'cover':
        default:
          contentBlock = `
            <div class="title-main" style="font-size: var(--title-size);">${titleVal}</div>
            <div class="hook-word">${hookVal}</div>
            <div class="body-text" >${bodyVal}</div>
          `;
          break;
      }

      const injectedHtml = templateStr
        .replace(/\{\{WIDTH\}\}/g, dimensions.width)
        .replace(/\{\{HEIGHT\}\}/g, dimensions.height)
        .replace(/\{\{BADGE_HTML\}\}/g, badgeHtml)
        .replace(/\{\{WATERMARK_NUMBER\}\}/g, watermarkNum)
        .replace(/\{\{SWIPE_ARROW_HTML\}\}/g, swipeArrowHtml)
        .replace(/\{\{BG_COLOR\}\}/g, customBg)
        .replace(/\{\{ACCENT_COLOR\}\}/g, customAccent)
        .replace(/\{\{LOGO_DISPLAY\}\}/g, displayLogo)
        .replace(/\{\{LOGO_SIZE\}\}/g, logoSize)
        .replace(/\{\{NICHE_COLOR\}\}/g, ambientColor)
        .replace(/\{\{OFFSET_Y\}\}/g, offsetY)
        .replace(/\{\{CONTENT_WIDTH\}\}/g, contentWidth)
        .replace(/\{\{TITLE_SIZE\}\}/g, titleSize)
        .replace(/\{\{BODY_SIZE\}\}/g, bodySize)
        .replace(/\{\{ICON_HTML\}\}/g, iconHtml)
        .replace(/\{\{CONTENT_BLOCK\}\}/g, contentBlock);

      await page.setContent(injectedHtml, { waitUntil: 'networkidle0', url: 'http://localhost:3000' });
      await page.evaluateHandle(() => document.fonts.ready);
      await page.evaluateHandle(() => Promise.all(Array.from(document.images).filter(img => !img.complete).map(img => new Promise(resolve => { img.onload = img.onerror = resolve; }))));

      const slidePngPath = path.join(tempDir, `slide_${i}_${timestamp}.png`);
      await page.screenshot({ path: slidePngPath, clip: { x: 0, y: 0, width: dimensions.width, height: dimensions.height } });

      archive.append(fs.createReadStream(slidePngPath), { name: `slide_${String(i + 1).padStart(2, '0')}.png` });
      
      // We can't delete the PNG here synchronously because archiver streams it asynchronously!
      // We will delete them after the archive is finalized.
    }

    await archive.finalize();
    await archivePromise; // Wait for write stream to close

    // Clean up individual PNGs
    for (let i = 0; i < slideDeck.length; i++) {
      const slidePngPath = path.join(tempDir, `slide_${i}_${timestamp}.png`);
      if (fs.existsSync(slidePngPath)) {
        fs.rmSync(slidePngPath, { force: true });
      }
    }

    res.setHeader('Content-Type', 'application/zip');
    res.setHeader('Content-Disposition', `attachment; filename="fit_biblia_studio_pro_${timestamp}.zip"`);
    return res.sendFile(zipPath, () => {
      fs.rmSync(zipPath, { force: true });
    });

  } catch (error) {
    console.error('Error generating slide deck:', error);
    res.status(500).json({ error: 'Failed to generate slide deck', details: error.message });
  } finally {
    if (page) await page.close().catch(e => console.error(e));
    if (browser) await browser.close().catch(e => console.error(e));
  }
});

app.listen(PORT, () => {
  console.log(`Fit Biblia Studio Pro Server running at http://localhost:${PORT}`);
});
