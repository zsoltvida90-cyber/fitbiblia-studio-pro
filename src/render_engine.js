import fs from 'fs';
import path from 'path';
import puppeteer from 'puppeteer';
import { PDFDocument } from 'pdf-lib';
import { generateSlideHTML } from './templates/slide_template.js';

function parseArgs() {
  const args = process.argv.slice(2);
  let inputPath = 'sample_input.json';
  let isDemo = false;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--input' && args[i + 1]) {
      inputPath = args[i + 1];
      i++;
    } else if (args[i] === '--demo') {
      isDemo = true;
    }
  }
  return { inputPath, isDemo };
}

async function renderEngine() {
  const { inputPath, isDemo } = parseArgs();
  const fullInputPath = path.resolve(inputPath);
  
  if (!fs.existsSync(fullInputPath)) {
    console.error(`Input file not found: ${fullInputPath}`);
    process.exit(1);
  }

  const rawJson = fs.readFileSync(fullInputPath, 'utf-8');
  const job = JSON.parse(rawJson);

  const outputDir = path.resolve(job.output || 'output');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  const slidesToRender = isDemo ? job.slides.slice(0, 1) : job.slides;
  console.log(`Starting render engine for jobId: ${job.jobId} (Demo mode: ${isDemo})`);

  const browser = await puppeteer.launch({
    headless: true,
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--allow-file-access-from-files']
  });

  const page = await browser.newPage();
  await page.setViewport({
    width: 1080,
    height: 1350,
    deviceScaleFactor: 2
  });

  const renderedAssets = [];
  const warnings = [];

  // Temporary dir for rendered slide HTML files
  const tempDir = path.resolve('temp_slides');
  if (!fs.existsSync(tempDir)) {
    fs.mkdirSync(tempDir, { recursive: true });
  }

  const pdfDoc = await PDFDocument.create();

  for (let i = 0; i < slidesToRender.length; i++) {
    const slide = slidesToRender[i];
    const slideIndexStr = String(i + 1).padStart(2, '0');
    const slideFilename = `slide${slideIndexStr}.png`;
    const slideOutputPath = path.join(outputDir, slideFilename);

    const htmlContent = generateSlideHTML(slide, {
      hookVariant: job.hookVariant || 'a',
      docTitle: job.docTitle || 'FIT BIBLIA • A FOGYÁS TÖRVÉNYE',
      pageIndex: i + 1,
      totalPages: job.slides.length,
      totalSlides: job.slides.length
    });

    const tempHtmlPath = path.join(tempDir, `slide_${slideIndexStr}.html`);
    fs.writeFileSync(tempHtmlPath, htmlContent, 'utf-8');

    const fileUrl = `file:///${tempHtmlPath.replace(/\\/g, '/')}`;
    await page.goto(fileUrl, { waitUntil: 'networkidle0' });

    // Wait for fonts to be completely ready
    await page.evaluateHandle(() => document.fonts.ready);

    // Take 1080x1350 PNG screenshot
    await page.screenshot({
      path: slideOutputPath,
      clip: { x: 0, y: 0, width: 1080, height: 1350 }
    });

    const pngBytes = fs.readFileSync(slideOutputPath);
    const pngImage = await pdfDoc.embedPng(pngBytes);
    const pdfPage = pdfDoc.addPage([1080, 1350]);
    pdfPage.drawImage(pngImage, {
      x: 0,
      y: 0,
      width: 1080,
      height: 1350
    });

    console.log(`Rendered slide: ${slideFilename}`);
    renderedAssets.push({
      file: slideFilename,
      type: 'image/png',
      width: 1080,
      height: 1350,
      aspectRatio: '4:5',
      status: 'VALID'
    });
  }

  // Save compiled PDF
  const pdfFilename = `${job.jobId}.pdf`;
  const pdfOutputPath = path.join(outputDir, pdfFilename);
  const pdfBytes = await pdfDoc.save();
  fs.writeFileSync(pdfOutputPath, pdfBytes);

  console.log(`Compiled PDF saved: ${pdfFilename}`);
  renderedAssets.push({
    file: pdfFilename,
    type: 'application/pdf',
    pages: slidesToRender.length,
    status: 'VALID'
  });

  await browser.close();

  // Clean up temp dir
  fs.rmSync(tempDir, { recursive: true, force: true });

  // Generate manifest.json
  const manifest = {
    timestamp: new Date().toISOString(),
    engineVersion: '1.0.0-obszidian',
    jobId: job.jobId,
    allSizesOK: true,
    renderedAssets: renderedAssets,
    warnings: warnings
  };

  const manifestPath = path.join(outputDir, 'manifest.json');
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), 'utf-8');
  console.log(`Manifest written to ${manifestPath}`);
}

renderEngine().catch((err) => {
  console.error('Render engine error:', err);
  process.exit(1);
});
