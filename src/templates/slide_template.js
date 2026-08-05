import fs from 'fs';
import path from 'path';

function escapeHtml(str) {
  if (typeof str !== 'string') return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

export function renderBaseTemplate(data) {
  const baseHtmlPath = path.resolve('templates/base_render.html');
  let rawHtml = '';
  if (fs.existsSync(baseHtmlPath)) {
    rawHtml = fs.readFileSync(baseHtmlPath, 'utf-8');
  } else {
    const srcBasePath = path.resolve('src/templates/base_render.html');
    if (fs.existsSync(srcBasePath)) {
      rawHtml = fs.readFileSync(srcBasePath, 'utf-8');
    }
  }

  const badge = escapeHtml(data.badge || data.headerLeft || 'INGYENES LEAD MAGNET');
  const title = escapeHtml(data.headline || data.title || 'A FOGYÁS TÖRVÉNYE');
  const hook = escapeHtml(data.hookWord || data.hook || '');
  const body = typeof data.body === 'string' ? escapeHtml(data.body) : renderBodyContent(data.body);

  return rawHtml
    .replace('{{BADGE}}', badge)
    .replace('{{TITLE}}', title)
    .replace('{{HOOK}}', hook)
    .replace('{{BODY}}', body);
}

function renderBodyContent(body) {
  if (Array.isArray(body)) {
    return body.map(chunk => {
      const text = escapeHtml(chunk.text || '');
      if (chunk.emphasis) {
        return `<span class="emphasis">${text}</span>`;
      }
      return text;
    }).join('');
  } else if (typeof body === 'string') {
    return escapeHtml(body);
  }
  return '';
}

function renderBulletList(items) {
  if (!Array.isArray(items) || items.length === 0) return '';
  const listItems = items.map(item => `<li class="bullet-item">${renderBodyContent(item)}</li>`).join('');
  return `<ul class="bullet-list">${listItems}</ul>`;
}

function renderFormulaCard(formula) {
  if (!formula) return '';
  const label = escapeHtml(formula.label || 'KÉPLET');
  const expression = escapeHtml(formula.expression || '');
  return `
    <div class="formula-card">
      <div class="formula-label">${label}</div>
      <div class="formula-expression">${expression}</div>
    </div>
  `;
}

function renderStatGrid(stats) {
  if (!Array.isArray(stats) || stats.length === 0) return '';
  const cards = stats.map(stat => `
    <div class="stat-card">
      <div class="stat-number">${escapeHtml(stat.number || '')}</div>
      <div class="stat-label">${escapeHtml(stat.label || '')}</div>
    </div>
  `).join('');
  return `<div class="stat-grid">${cards}</div>`;
}

function renderKeyPointsBox(keyPoints) {
  if (!keyPoints) return '';
  const title = escapeHtml(keyPoints.title || 'LÉNYEG');
  const text = renderBodyContent(keyPoints.text);
  return `
    <div class="key-points-box">
      <div class="key-points-title">${title}</div>
      <div class="key-points-text">${text}</div>
    </div>
  `;
}

export function generateSlideHTML(slide, options = {}) {
  if (options.useBaseTemplate) {
    return renderBaseTemplate(slide);
  }

  const hookVariant = options.hookVariant || 'a';
  const nicheClass = slide.niche ? `glow--${slide.niche}` : '';
  
  // Headline hookWord replacement
  let headlineHtml = escapeHtml(slide.headline || slide.title || '');
  if (slide.hookWord && headlineHtml && headlineHtml.includes(slide.hookWord)) {
    const escapedHook = escapeHtml(slide.hookWord);
    const hookMarkup = `<span class="hook-word">${escapedHook}</span>`;
    headlineHtml = headlineHtml.replace(escapedHook, hookMarkup);
  }

  const bodyHtml = renderBodyContent(slide.body);
  const bulletListHtml = renderBulletList(slide.items);
  const formulaHtml = renderFormulaCard(slide.formula);
  const statGridHtml = renderStatGrid(slide.stats);
  const keyPointsHtml = renderKeyPointsBox(slide.keyPoints);

  const headerLeft = escapeHtml(slide.headerLeft || slide.badge || 'BIZONYÍTÉK-ALAPÚ KIVONAT');
  const docTitle = escapeHtml(options.docTitle || slide.docTitle || 'FIT BIBLIA • A FOGYÁS TÖRVÉNYE');
  const pageCountStr = slide.folio || `${String(options.pageIndex || 1).padStart(2, '0')} / ${String(options.totalPages || 4).padStart(2, '0')}`;

  const headerBarHtml = `
    <div class="header-bar">
      <span class="header-left-label">${headerLeft}</span>
      <span class="header-brand-wordmark">FIT BIBLIA</span>
    </div>
  `;

  const footerBarHtml = `
    <div class="footer-bar">
      <span class="footer-doc-title">${docTitle}</span>
      <span class="footer-page-count">${escapeHtml(pageCountStr)}</span>
    </div>
  `;

  const nicheHtml = slide.niche ? `<div class="niche-glow ${nicheClass}"></div>` : '';

  let mainContent = '';

  switch (slide.type) {
    case 'cover':
      mainContent = `
        ${headerBarHtml}
        <div class="content-container" style="justify-content: center; align-items: flex-start;">
          ${slide.badge ? `<div class="cover-badge">${escapeHtml(slide.badge)}</div>` : ''}
          <h1 class="headline-cover">${headlineHtml}</h1>
          ${slide.subtitle ? `<div class="subtitle" style="margin-bottom: 24px;">${escapeHtml(slide.subtitle)}</div>` : ''}
          ${keyPointsHtml}
        </div>
        ${footerBarHtml}
      `;
      break;

    case 'inner':
    case 'content':
      mainContent = `
        ${headerBarHtml}
        <div class="content-container" style="padding-top: 150px;">
          <h2 class="headline-inner">${headlineHtml}</h2>
          ${bodyHtml ? `<div class="body-text" style="margin-bottom: 20px;">${bodyHtml}</div>` : ''}
          ${formulaHtml}
          ${statGridHtml}
          ${bulletListHtml}
          ${keyPointsHtml}
        </div>
        ${footerBarHtml}
      `;
      break;

    case 'formula':
      mainContent = `
        ${headerBarHtml}
        <div class="content-container" style="padding-top: 150px;">
          <h2 class="headline-inner">${headlineHtml}</h2>
          ${bodyHtml ? `<div class="body-text">${bodyHtml}</div>` : ''}
          ${formulaHtml}
          ${keyPointsHtml}
        </div>
        ${footerBarHtml}
      `;
      break;

    case 'stat':
      mainContent = `
        ${headerBarHtml}
        <div class="content-container" style="padding-top: 150px;">
          <h2 class="headline-inner">${headlineHtml}</h2>
          ${statGridHtml}
          ${bodyHtml ? `<div class="body-text">${bodyHtml}</div>` : ''}
          ${bulletListHtml}
        </div>
        ${footerBarHtml}
      `;
      break;

    case 'cta':
    case 'closing':
      mainContent = `
        ${headerBarHtml}
        <div class="content-container" style="justify-content: center; align-items: flex-start;">
          <h1 class="headline-cover" style="font-size: 76px; line-height: 90px;">${headlineHtml}</h1>
          ${slide.subtitle ? `<div class="subtitle">${escapeHtml(slide.subtitle)}</div>` : ''}
          <div class="cta-banner">
            <div class="body-text" style="font-size: 34px; line-height: 52px; color: var(--color-bone);">
              ${bodyHtml || 'Töltsd le a teljes 39 oldalas bizonyíték-alapú útmutatót és lépj a cselekvés útjára!'}
            </div>
            ${slide.ctaText ? `
              <div class="cta-button">
                <span>${escapeHtml(slide.ctaText)}</span>
              </div>
            ` : ''}
          </div>
        </div>
        ${footerBarHtml}
      `;
      break;

    default:
      mainContent = `
        ${headerBarHtml}
        <div class="content-container" style="padding-top: 150px;">
          <h2 class="headline-inner">${headlineHtml}</h2>
          <div class="body-text">${bodyHtml}</div>
          ${bulletListHtml}
        </div>
        ${footerBarHtml}
      `;
  }

  return `<!DOCTYPE html>
<html lang="hu">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=1080, height=1350, initial-scale=1.0" />
  <link rel="stylesheet" href="../src/styles/obszidian.css" />
</head>
<body>
  <div class="slide-canvas">
    <svg class="grain-layer" xmlns="http://www.w3.org/2000/svg">
      <filter id="grain">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" seed="42" />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width="100%" height="100%" filter="url(#grain)" />
    </svg>
    ${nicheHtml}
    ${mainContent}
  </div>
</body>
</html>`;
}
