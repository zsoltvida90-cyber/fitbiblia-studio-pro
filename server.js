import express from 'express';
import cors from 'cors';
import path from 'path';
import fs from 'fs';
import puppeteer from 'puppeteer';
import { PDFDocument } from 'pdf-lib';
import sqlite3 from 'sqlite3';
import dotenv from 'dotenv';
dotenv.config();
import { GoogleGenAI } from '@google/genai';
import multer from 'multer';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const archiver = require('archiver');
const pdfParse = require('pdf-parse');
import { launchBrowser, buildSelfContainedDocument, mapWebSlideToEngine } from './src/render_page.js';

// Initialize Google Gemini AI client
const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

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

// Helper: Strict JSON Validation & Normalization for slide decks
function validateSlideDeck(deck) {
  if (!Array.isArray(deck)) return [];
  
  return deck.map((slide, index) => {
    // Ensure slide is an object
    if (!slide || typeof slide !== 'object') slide = {};

    // Validate type
    const validTypes = ['cover', 'inner', 'myth', 'stat', 'cta'];
    let type = slide.type || slide.slideType;
    if (!validTypes.includes(type)) type = 'cover';

    // Normalize and fallback string fields
    const headline = typeof slide.headline === 'string' ? slide.headline : (typeof slide.title === 'string' ? slide.title : 'A FOGYÁS TÖRVÉNYE');
    const badge = typeof slide.badge === 'string' ? slide.badge : (typeof slide.headerLeft === 'string' ? slide.headerLeft : '');
    const hookWord = typeof slide.hookWord === 'string' ? slide.hookWord : (typeof slide.hook === 'string' ? slide.hook : '');
    const icon = typeof slide.icon === 'string' ? slide.icon : 'none';
    
    let body = '';
    if (typeof slide.body === 'string') {
      body = slide.body;
    } else if (Array.isArray(slide.body)) {
      body = slide.body.map(b => typeof b === 'string' ? b : (b.text || '')).join('');
    }

    return {
      type,
      badge,
      headline,
      hookWord,
      body,
      icon,
      offsetY: typeof slide.offsetY === 'number' ? slide.offsetY : 0,
      contentWidth: typeof slide.contentWidth === 'number' ? slide.contentWidth : 888,
      titleSize: slide.titleSize,
      bodySize: slide.bodySize
    };
  });
}

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

// Helper: Render Slide to Image
async function renderSlideToImage(page, slide, config, index, tempDir) {
  const { dimensions, timestamp } = config;
  
  // 1. Map generic web UI slide to the powerful Obszidián engine format
  const engineSlide = mapWebSlideToEngine(slide);
  
  // 2. Build the self-contained HTML (all fonts + CSS inlined)
  const injectedHtml = buildSelfContainedDocument(engineSlide, {
    docTitle: 'FIT BIBLIA',
    pageIndex: index + 1,
    totalPages: 10 // Approximation, could be config.totalPages
  });

  // 3. Load it into the headless browser
  await page.setContent(injectedHtml, { waitUntil: 'load' });
  await page.evaluateHandle(() => document.fonts.ready);
  await page.evaluateHandle(() => Promise.all(Array.from(document.images).filter(img => !img.complete).map(img => new Promise(resolve => { img.onload = img.onerror = resolve; }))));

  // Dynamic typography scaling: shrink sizes if content overflows
  await page.evaluate(() => {
    const container = document.querySelector('.slide-container');
    const contentArea = document.querySelector('.content-area');
    if (!container || !contentArea) return;

    let maxLoops = 25;
    while (container.scrollHeight > container.clientHeight && maxLoops > 0) {
      let currentTitle = parseInt(getComputedStyle(container).getPropertyValue('--title-size'));
      let currentBody = parseInt(getComputedStyle(container).getPropertyValue('--body-size'));
      
      let scaled = false;
      if (currentTitle > 30) {
        container.style.setProperty('--title-size', (currentTitle - 2) + 'px');
        scaled = true;
      }
      if (currentBody > 18) {
        container.style.setProperty('--body-size', (currentBody - 1) + 'px');
        scaled = true;
      }
      
      if (!scaled) break; // Cannot shrink further
      maxLoops--;
    }
  });

  const slidePngPath = path.join(tempDir, `slide_${index}_${timestamp}.png`);
  await page.screenshot({ path: slidePngPath, clip: { x: 0, y: 0, width: dimensions.width, height: dimensions.height } });
  
  return slidePngPath;
}


const upload = multer({ dest: 'temp_web/uploads/' });

// API Route: POST /api/parse-pdf (Server-side PDF Extraction)
app.post('/api/parse-pdf', upload.single('pdf'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'Nincs PDF fájl feltöltve.' });
    }

    const dataBuffer = fs.readFileSync(req.file.path);
    const pdfData = await pdfParse(dataBuffer);
    const extractedText = pdfData.text;

    // Clean up uploaded file
    fs.unlinkSync(req.file.path);

    if (!extractedText || extractedText.trim() === '') {
      return res.status(400).json({ error: 'Nem sikerült szöveget kinyerni a PDF-ből.' });
    }

    res.json({ text: extractedText });

  } catch (err) {
    console.error('PDF parsing error:', err);
    res.status(500).json({ error: 'Hiba a PDF feldolgozása során' });
  }
});

// API Route: POST /api/parse-ai (Google Gemini Integration)
app.post('/api/parse-ai', async (req, res) => {
  try {
    const { text } = req.body;
    
    if (!process.env.GEMINI_API_KEY || process.env.GEMINI_API_KEY === 'ide_masold_be_a_kulcsot') {
      return res.status(400).json({ error: 'Nincs beállítva a GEMINI_API_KEY a .env fájlban!' });
    }

    const systemPrompt = `
      You are an expert copywriter and content strategist for a fitness brand.
      Extract the provided text into a JSON array of slide objects.
      Each object MUST have the following properties:
      - type: "cover", "inner", "stat", "myth", or "cta".
      - badge: Short uppercase text (e.g., "01. FEJEZET").
      - headline: Main title (e.g., "Energiamérleg Szabálya").
      - hookWord: One or two short words for visual emphasis (e.g., "-500 kcal").
      - body: The main body paragraph.
      - icon: "flame", "target", "brain", "book", "check", or "alert".
      Return ONLY valid JSON wrapped in { "slides": [ ... ] }.
    `;

    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: [
        { role: 'user', parts: [{ text: systemPrompt + '\n\n' + text }] }
      ],
      config: {
        responseMimeType: 'application/json',
        temperature: 0.7
      }
    });

    const parsedResponse = JSON.parse(response.text);
    const validatedSlides = validateSlideDeck(parsedResponse.slides || []);

    res.json({ slides: validatedSlides });
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
    
    const slideDeck = validateSlideDeck(Array.isArray(slides) ? slides : [slide || req.body]);
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

    browser = await launchBrowser();

    page = await browser.newPage();
    await page.setViewport({ width: dimensions.width, height: dimensions.height, deviceScaleFactor: 2 });

    const pdfDoc = await PDFDocument.create();
    const timestamp = Date.now();

    const config = { dimensions, customBg, customAccent, displayLogo, logoSize, globalTitleSize, globalBodySize, ambientColor, templateStr, timestamp };

    for (let i = 0; i < slideDeck.length; i++) {
      const slidePngPath = await renderSlideToImage(page, slideDeck[i], config, i, tempDir);

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
    
    const slideDeck = validateSlideDeck(Array.isArray(slides) ? slides : [slide || req.body]);
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

    browser = await launchBrowser();

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

    const config = { dimensions, customBg, customAccent, displayLogo, logoSize, globalTitleSize, globalBodySize, ambientColor, templateStr, timestamp };
    let generatedFiles = [];

    try {
      // Parallel Chunking Logic (Concurrency Limit: 4)
      const CHUNK_SIZE = 4;
      for (let i = 0; i < slideDeck.length; i += CHUNK_SIZE) {
        const chunk = slideDeck.slice(i, i + CHUNK_SIZE);
        const chunkPromises = chunk.map(async (slide, chunkIndex) => {
          const absoluteIndex = i + chunkIndex;
          const localPage = await browser.newPage();
          await localPage.setViewport({ width: dimensions.width, height: dimensions.height, deviceScaleFactor: 2 });
          try {
            return await renderSlideToImage(localPage, slide, config, absoluteIndex, tempDir);
          } finally {
            await localPage.close().catch(e => console.error('Error closing page:', e));
          }
        });
        
        const chunkResults = await Promise.all(chunkPromises);
        generatedFiles.push(...chunkResults);
      }

      generatedFiles.forEach((img, idx) => {
        if (fs.existsSync(img)) {
          const slideType = slideDeck[idx].type || 'slide';
          archive.append(fs.createReadStream(img), { name: `slide_${String(idx + 1).padStart(2, '0')}_${slideType}.png` });
        }
      });

      await archive.finalize();
      await archivePromise; // Wait for write stream to close
    } finally {
      // Clean up individual PNGs regardless of success/failure
      generatedFiles.forEach(file => {
        if (fs.existsSync(file)) {
          fs.rmSync(file, { force: true });
        }
      });
    }

    res.setHeader('Content-Type', 'application/zip');
    res.setHeader('Content-Disposition', `attachment; filename="fit_biblia_studio_pro_${timestamp}.zip"`);
    return res.sendFile(zipPath, () => {
      fs.rmSync(zipPath, { force: true });
    });

  } catch (error) {
    console.error('Error generating batch export:', error);
    res.status(500).json({ error: 'Failed to generate batch export', details: error.message });
  } finally {
    if (browser) await browser.close().catch(e => console.error(e));
  }
});

app.listen(PORT, () => {
  console.log(`Fit Biblia Studio Pro Server running at http://localhost:${PORT}`);
});
