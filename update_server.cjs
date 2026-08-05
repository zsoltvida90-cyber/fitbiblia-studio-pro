const fs = require('fs');
const path = require('path');

const serverPath = path.resolve('server.js');
let server = fs.readFileSync(serverPath, 'utf-8');

// 1. Add imports and DB initialization
const importsToAdd = `import sqlite3 from 'sqlite3';
import archiver from 'archiver';

const dbPath = path.resolve('projects.db');
const db = new sqlite3.Database(dbPath, (err) => {
  if (err) {
    console.error('Error opening database', err.message);
  } else {
    db.run(\`CREATE TABLE IF NOT EXISTS projects (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      deck_json TEXT NOT NULL,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )\`);
  }
});`;

server = server.replace("import { PDFDocument } from 'pdf-lib';", "import { PDFDocument } from 'pdf-lib';\n" + importsToAdd);


// 2. Add projects routes
const projectsRoutes = `
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
`;

server = server.replace('// API Route: POST /api/parse-text', projectsRoutes + '\n// API Route: POST /api/parse-text');


// 3. Add Export Batch Route
const exportBatchRoute = `
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
    const zipPath = path.join(tempDir, \`export_deck_\${timestamp}.zip\`);
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

      const badgeHtml = badgeVal ? \`<div class="badge-clean">\${badgeVal}</div>\` : \`<div></div>\`;
      const watermarkNum = (slideType === 'cover') ? '' : String(i + 1);

      let contentBlock = '';
      switch (slideType) {
        case 'cta':
          contentBlock = \`
            <div class="title-main" >\${titleVal}</div>
            <div class="body-text" style="margin-top: 20px;">\${bodyVal}</div>
            <div class="ig-action-bar">
              <div>[ ♥ LIKE ]</div>
              <div>[ 💬 COMMENT ]</div>
              <div>[ ✈ SHARE ]</div>
              <div>[ 💾 SAVE ]</div>
            </div>
          \`;
          break;
        case 'inner':
          contentBlock = \`
            <div class="body-text" style="font-family: 'Archivo', sans-serif; color: #E8DFC9; text-transform: uppercase; margin-bottom: 20px; font-size: var(--title-size);">\${titleVal}</div>
            <div class="body-text" >\${bodyVal}</div>
          \`;
          break;
        case 'myth':
          contentBlock = \`
            <div style="background: rgba(110, 36, 51, 0.15); border: 1px solid rgba(110, 36, 51, 0.5); padding: 32px; border-radius: 12px; margin-bottom: 20px;">
              <div style="font-family: 'IBM Plex Mono', monospace; color: #FF54A6; font-weight: 600; margin-bottom: 12px; font-size: 18px; letter-spacing: 1.5px;">TÉVHIT / MÍTOSZ</div>
              <div class="body-text" style="font-size: var(--title-size);">\${titleVal}</div>
            </div>
            <div style="background: rgba(37, 230, 122, 0.08); border: 1px solid rgba(37, 230, 122, 0.4); padding: 32px; border-radius: 12px;">
              <div style="font-family: 'IBM Plex Mono', monospace; color: #25E67A; font-weight: 600; margin-bottom: 12px; font-size: 18px; letter-spacing: 1.5px;">VALÓSÁG / TUDOMÁNY</div>
              <div class="body-text" >\${bodyVal}</div>
            </div>
          \`;
          break;
        case 'stat':
          contentBlock = \`
            <div class="body-text" style="font-family: 'Archivo', sans-serif; font-size: var(--title-size); font-weight: 800; color: #E8DFC9; text-transform: uppercase;">\${titleVal}</div>
            <div style="font-family: 'Archivo', sans-serif; font-size: 110px; font-weight: 900; color: var(--accent); line-height: 1; margin: 20px 0;">\${hookVal}</div>
            <div class="body-text" >\${bodyVal}</div>
          \`;
          break;
        case 'cover':
        default:
          contentBlock = \`
            <div class="title-main" style="font-size: var(--title-size);">\${titleVal}</div>
            <div class="hook-word">\${hookVal}</div>
            <div class="body-text" >\${bodyVal}</div>
          \`;
          break;
      }

      const injectedHtml = templateStr
        .replace(/\\{\\{WIDTH\\}\\}/g, dimensions.width)
        .replace(/\\{\\{HEIGHT\\}\\}/g, dimensions.height)
        .replace(/\\{\\{BADGE_HTML\\}\\}/g, badgeHtml)
        .replace(/\\{\\{WATERMARK_NUMBER\\}\\}/g, watermarkNum)
        .replace(/\\{\\{SWIPE_ARROW_HTML\\}\\}/g, swipeArrowHtml)
        .replace(/\\{\\{BG_COLOR\\}\\}/g, customBg)
        .replace(/\\{\\{ACCENT_COLOR\\}\\}/g, customAccent)
        .replace(/\\{\\{LOGO_DISPLAY\\}\\}/g, displayLogo)
        .replace(/\\{\\{LOGO_SIZE\\}\\}/g, logoSize)
        .replace(/\\{\\{NICHE_COLOR\\}\\}/g, ambientColor)
        .replace(/\\{\\{OFFSET_Y\\}\\}/g, offsetY)
        .replace(/\\{\\{CONTENT_WIDTH\\}\\}/g, contentWidth)
        .replace(/\\{\\{TITLE_SIZE\\}\\}/g, titleSize)
        .replace(/\\{\\{BODY_SIZE\\}\\}/g, bodySize)
        .replace(/\\{\\{ICON_HTML\\}\\}/g, iconHtml)
        .replace(/\\{\\{CONTENT_BLOCK\\}\\}/g, contentBlock);

      await page.setContent(injectedHtml, { waitUntil: 'networkidle0', url: 'http://localhost:3000' });
      await page.evaluateHandle(() => document.fonts.ready);
      await page.evaluateHandle(() => Promise.all(Array.from(document.images).filter(img => !img.complete).map(img => new Promise(resolve => { img.onload = img.onerror = resolve; }))));

      const slidePngPath = path.join(tempDir, \`slide_\${i}_\${timestamp}.png\`);
      await page.screenshot({ path: slidePngPath, clip: { x: 0, y: 0, width: dimensions.width, height: dimensions.height } });

      archive.append(fs.createReadStream(slidePngPath), { name: \`slide_\${String(i + 1).padStart(2, '0')}.png\` });
      
      // We can't delete the PNG here synchronously because archiver streams it asynchronously!
      // We will delete them after the archive is finalized.
    }

    await archive.finalize();
    await archivePromise; // Wait for write stream to close

    // Clean up individual PNGs
    for (let i = 0; i < slideDeck.length; i++) {
      const slidePngPath = path.join(tempDir, \`slide_\${i}_\${timestamp}.png\`);
      if (fs.existsSync(slidePngPath)) {
        fs.rmSync(slidePngPath, { force: true });
      }
    }

    res.setHeader('Content-Type', 'application/zip');
    res.setHeader('Content-Disposition', \`attachment; filename="fit_biblia_studio_pro_\${timestamp}.zip"\`);
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
`;

server = server.replace('app.listen(PORT, () => {', exportBatchRoute + '\napp.listen(PORT, () => {');

fs.writeFileSync(serverPath, server, 'utf-8');
console.log('Updated server.js');
