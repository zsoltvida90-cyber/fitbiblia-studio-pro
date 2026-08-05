import fs from 'fs';
import path from 'path';
import puppeteer from 'puppeteer';
import express from 'express';

const masterFile = path.resolve('FB4.0_30day_master_FULL.txt');
const outputDir = path.resolve('output');

// Clean Output
if (fs.existsSync(outputDir)) {
    fs.rmSync(outputDir, { recursive: true, force: true });
}
fs.mkdirSync(outputDir, { recursive: true });

// Start local server to serve assets for Puppeteer
const app = express();
app.use('/assets', express.static(path.resolve('assets')));
const server = app.listen(3001, () => {
    console.log('Ideiglenes szerver elindítva az assetekhez a 3001-es porton.');
});

// Helper: Format dimensions map
function getCanvasDimensions(canvasFormat) {
    switch (canvasFormat) {
        case 'story': return { width: 1080, height: 1920 };
        case 'pdf': return { width: 1240, height: 1754 };
        case 'carousel':
        default: return { width: 1080, height: 1350 };
    }
}

function getIconHtml(iconName, accentColor) {
    if (!iconName || iconName === 'none') return '';
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

function getSwipeArrowHtml(slideType, accentColor) {
    if (slideType === 'cover' || slideType === 'cta') return '';
    return `
      <div class="swipe-arrow" style="position: absolute; right: 40px; bottom: 15%; color: var(--accent); opacity: 0.6; z-index: 10;">
        <svg width="40" height="60" viewBox="0 0 24 40" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="8 12 16 20 8 28"></polyline>
        </svg>
      </div>
    `;
}

function parseTextToSlides(text) {
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
            badge: layout === 'cover' ? '' : (layout === 'cta' ? 'KÖVESS MINKET' : `0${slides.length + 1}. SLIDE`),
            headline: titleVal.toUpperCase(),
            hookWord: hookVal,
            body: bodyVal,
            icon: layout === 'cover' ? 'flame' : (layout === 'stat' ? 'target' : (layout === 'cta' ? 'check' : 'book')),
            offsetY: 0,
            contentWidth: 888
        });
    });
    return slides;
}

async function runBatch() {
    console.log('Olvasom a forrásfájlt:', masterFile);
    const textContent = fs.readFileSync(masterFile, 'utf8');

    const days = textContent.split(/NAP \d+ - [^\n]+/g).slice(1);
    const dayHeaders = [...textContent.matchAll(/NAP (\d+) - [^\n]+/g)];

    console.log(`Talált napok száma: ${days.length}`);

    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--allow-file-access-from-files']
    });

    const baseTemplatePath = path.resolve('templates/base_render.html');
    const templateStr = fs.readFileSync(baseTemplatePath, 'utf-8');

    for (let i = 0; i < days.length; i++) {
        const dayNumber = dayHeaders[i][1].padStart(2, '0');
        const dayContent = days[i];

        if (!/S1\:/i.test(dayContent)) {
            console.log(`[Nap ${dayNumber}] Nem tartalmaz Carousel slide-okat, kihagyás.`);
            continue;
        }

        const s1Index = dayContent.search(/S1\:/i);
        const nextContentIndex = dayContent.indexOf('[19:30]');
        let carouselContent = dayContent.substring(s1Index, nextContentIndex !== -1 ? nextContentIndex : dayContent.length);

        const slides = parseTextToSlides(carouselContent);

        if (slides.length === 0) continue;

        console.log(`[Nap ${dayNumber}] Feldolgozás... (${slides.length} slide)`);

        const dayDir = path.join(outputDir, `day_${dayNumber}`);
        if (!fs.existsSync(dayDir)) {
            fs.mkdirSync(dayDir, { recursive: true });
        }

        const page = await browser.newPage();
        const dimensions = getCanvasDimensions('carousel');
        await page.setViewport({ width: dimensions.width, height: dimensions.height, deviceScaleFactor: 2 });

        const customBg = '#0A0B0D'; // Obsidian dark theme as requested
        const customAccent = '#E6C15A'; // Gold
        const displayLogo = 'block';
        const logoSize = 80;
        const ambientColor = '#E6C15A'; // Gold ambient glow

        for (let s = 0; s < slides.length; s++) {
            const currentSlide = slides[s];
            const slideType = currentSlide.type || 'cover';
            const badgeVal = currentSlide.badge || '';
            const titleVal = currentSlide.headline || '';
            const hookVal = currentSlide.hookWord || '';
            const bodyVal = currentSlide.body || '';
            const iconHtml = getIconHtml(currentSlide.icon, customAccent);
            const swipeArrowHtml = getSwipeArrowHtml(slideType, customAccent);
            const badgeHtml = badgeVal ? `<div class="badge-clean">${badgeVal}</div>` : `<div></div>`;
            const watermarkNum = (slideType === 'cover') ? '' : String(s + 1);

            let contentBlock = '';
            switch (slideType) {
                case 'cta':
                    contentBlock = `
                        <div class="title-main">${titleVal}</div>
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
                        <div class="body-text">${bodyVal}</div>
                    `;
                    break;
                case 'stat':
                    contentBlock = `
                        <div class="body-text" style="font-family: 'Archivo', sans-serif; font-size: var(--title-size); font-weight: 800; color: #E8DFC9; text-transform: uppercase;">${titleVal}</div>
                        <div style="font-family: 'Archivo', sans-serif; font-size: 110px; font-weight: 900; color: var(--accent); line-height: 1; margin: 20px 0;">${hookVal}</div>
                        <div class="body-text">${bodyVal}</div>
                    `;
                    break;
                case 'cover':
                default:
                    contentBlock = `
                        <div class="title-main" style="font-size: var(--title-size);">${titleVal}</div>
                        <div class="hook-word">${hookVal}</div>
                        <div class="body-text">${bodyVal}</div>
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
                .replace(/\{\{OFFSET_Y\}\}/g, 0)
                .replace(/\{\{CONTENT_WIDTH\}\}/g, 888)
                .replace(/\{\{TITLE_SIZE\}\}/g, 60)
                .replace(/\{\{BODY_SIZE\}\}/g, 26)
                .replace(/\{\{ICON_HTML\}\}/g, iconHtml)
                .replace(/\{\{CONTENT_BLOCK\}\}/g, contentBlock);

            await page.setContent(injectedHtml, { waitUntil: 'networkidle0', url: 'http://localhost:3001' });
            
            // Try to wait for fonts and images
            try {
                await page.evaluateHandle(() => document.fonts.ready);
                await page.evaluateHandle(() => Promise.all(Array.from(document.images).filter(img => !img.complete).map(img => new Promise(resolve => { img.onload = img.onerror = resolve; }))));
            } catch(e) {}

            const slidePngPath = path.join(dayDir, `slide_${(s + 1).toString().padStart(2, '0')}.png`);
            await page.screenshot({ path: slidePngPath, clip: { x: 0, y: 0, width: dimensions.width, height: dimensions.height } });
        }
        await page.close();
        console.log(`[Nap ${dayNumber}] Kész.`);
    }

    await browser.close();
    server.close();
    console.log('Batch generálás sikeresen befejeződött!');
}

runBatch().catch(err => {
    console.error(err);
    server.close();
});
