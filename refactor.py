import re
import os

# 1. Update public/index.html
index_path = 'public/index.html'
with open(index_path, 'r', encoding='utf-8') as f:
    content = f.read()

# CSS Updates in index.html
content = re.sub(r'\.brand-logo-img\s*\{\s*object-fit: contain;\s*\}', 
                 '.brand-logo-img {\n      height: var(--logo-size);\n      object-fit: contain;\n    }', content)

content = re.sub(r'\.icon-box\s*\{\s*width: 64px;\s*height: 64px;\s*margin-bottom: 25px;\s*filter: drop-shadow\(0px 4px 10px rgba\(230, 193, 90, 0\.3\)\);\s*\}',
                 '.icon-box {\n      width: 64px;\n      height: 64px;\n      margin-bottom: 25px;\n      color: var(--accent);\n      filter: drop-shadow(0px 4px 10px rgba(230, 193, 90, 0.3));\n    }', content)

content = re.sub(r'\.title-main\s*\{\s*font-family: \'Archivo\', sans-serif;\s*font-weight: 900;',
                 '.title-main {\n      font-family: \'Archivo\', sans-serif;\n      font-size: var(--title-size);\n      font-weight: 900;', content)

content = re.sub(r'\.body-text\s*\{\s*line-height: 1\.6;\s*color: #C7BEAB;\s*\}',
                 '.body-text {\n      font-size: var(--body-size);\n      line-height: 1.6;\n      color: #C7BEAB;\n    }', content)

content = re.sub(r'(\.ig-action-bar\s*\{[^}]+)(letter-spacing: 1\.5px;\s*\})',
                 r'\1\2\n      color: var(--accent);', content)

# JS Updates in index.html

# Debounce function & Event Listeners update
js_listeners = '''    function debounce(func, wait) {
      let timeout;
      return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
      };
    }

    const debouncedUpdatePreview = debounce(() => {
      syncActiveSlideFromForm();
      updatePreview();
    }, 150);

    // Form Change Listeners for Instant Live Updating
    document.querySelectorAll('input, select, textarea').forEach(el => {
      el.addEventListener('input', debouncedUpdatePreview);
      el.addEventListener('change', debouncedUpdatePreview);
    });'''

content = re.sub(r'    // Form Change Listeners for Instant Live Updating\s*document\.querySelectorAll\(\'input, select, textarea\'\)\.forEach\(el => \{\s*el\.addEventListener\(\'input\', \(\) => \{\s*syncActiveSlideFromForm\(\);\s*updatePreview\(\);\s*\}\);\s*el\.addEventListener\(\'change\', \(\) => \{\s*syncActiveSlideFromForm\(\);\s*updatePreview\(\);\s*\}\);\s*\}\);', js_listeners, content)

# updatePreview removal of syncActiveSlideFromForm
content = content.replace('      syncActiveSlideFromForm();\n      const multiSlidePreview = document.getElementById(\'multiSlidePreview\');',
                          '      // syncActiveSlideFromForm(); // Debounced outside\n      const multiSlidePreview = document.getElementById(\'multiSlidePreview\');')

# getIconSvg update
content = content.replace('const styleAttr = `style=\"color: ${color}; filter: drop-shadow(0px 4px 10px rgba(230,193,90,0.3)); width: 64px; height: 64px; margin-bottom: 25px;\" class=\"icon-box\"`;',
                          'const styleAttr = `class=\"icon-box\"`;')
content = re.sub(r'stroke=\"\$\{color\}\"', 'stroke="var(--accent)"', content)

# getSwipeArrowSvg update
content = content.replace('style=\"position: absolute; right: 40px; bottom: 15%; color: ${color}; opacity: 0.6; z-index: 10;\"',
                          'style=\"position: absolute; right: 40px; bottom: 15%; color: var(--accent); opacity: 0.6; z-index: 10;\"')

# renderSlideTabs update (remove onclick, add data-idx)
content = content.replace('onclick=\"selectSlide(${idx})\"', 'data-idx=\"${idx}\"')

# add event listener for slideList
add_btn_listener = '''    document.getElementById('addSlideBtn').addEventListener('click', () => {'''
slide_list_listener = '''    document.getElementById('slideList').addEventListener('click', (e) => {
      const btn = e.target.closest('button');
      if (!btn || !btn.dataset.idx) return;
      selectSlide(parseInt(btn.dataset.idx, 10));
    });

    document.getElementById('addSlideBtn').addEventListener('click', () => {'''
content = content.replace(add_btn_listener, slide_list_listener)

# selectSlide update to use requestAnimationFrame for scrollIntoView
content = re.sub(r'    function selectSlide\(idx\) \{\s*activeSlideIndex = idx;\s*renderSlideTabs\(\);\s*updatePreview\(\);\s*const currentSlideObj.*?\}\s*\}', 
'''    function selectSlide(idx) {
      activeSlideIndex = idx;
      renderSlideTabs();
      updatePreview();
      requestAnimationFrame(() => {
        const currentSlideObj = slideDeck[idx];
        const targetId = currentSlideObj && currentSlideObj.id ? `preview-slide-${currentSlideObj.id}` : `preview-slide-idx-${idx}`;
        const targetEl = document.getElementById(targetId);
        if (targetEl) {
          targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      });
    }''', content, flags=re.DOTALL)

# Inject CSS vars in updatePreview container
content = content.replace('<div style=\"width: ${dimensions.w}px; height: ${dimensions.h}px; transform: scale(${dimensions.scale}); transform-origin: top center; background-color: ${bgColor}; font-family: \'Inter\', sans-serif; position: relative;\"',
                          '<div style=\"width: ${dimensions.w}px; height: ${dimensions.h}px; transform: scale(${dimensions.scale}); transform-origin: top center; background-color: ${bgColor}; font-family: \'Inter\', sans-serif; position: relative; --title-size: ${globalTitleSize}px; --body-size: ${globalBodySize}px; --logo-size: ${logoSize}px; --accent: ${accentColor};\"')

# Remove inline styles from contentBlock strings
content = re.sub(r'style="font-size: \$\{globalTitleSize\}px;\s*color: #E8DFC9;\s*text-transform: uppercase;"', '', content)
content = re.sub(r'style="font-size: \$\{globalBodySize\}px;\s*margin-top: 20px;"', 'style="margin-top: 20px;"', content)
content = re.sub(r'style="color: \$\{accentColor\};"', '', content) # ig-action-bar
content = re.sub(r'style="font-size: \$\{globalTitleSize\}px;\s*font-family: \'Archivo\', sans-serif;\s*color: #E8DFC9;\s*text-transform: uppercase;\s*margin-bottom: 20px;"', 'style="font-family: \'Archivo\', sans-serif; color: #E8DFC9; text-transform: uppercase; margin-bottom: 20px; font-size: var(--title-size);"', content) # inner slide
content = re.sub(r'style="font-size: \$\{globalBodySize\}px;"', '', content) # inner body, myth body
content = re.sub(r'style="font-size: \$\{globalTitleSize\}px;"', 'style="font-size: var(--title-size);"', content) # myth title
content = re.sub(r'style="font-family: \'Archivo\', sans-serif;\s*font-size: \$\{globalTitleSize\}px;\s*font-weight: 800;\s*color: #E8DFC9;\s*text-transform: uppercase;"', 'style="font-family: \'Archivo\', sans-serif; font-size: var(--title-size); font-weight: 800; color: #E8DFC9; text-transform: uppercase;"', content) # stat title
content = re.sub(r'style="font-family: \'Archivo\', sans-serif;\s*font-size: 110px;\s*font-weight: 900;\s*color: \$\{accentColor\};\s*line-height: 1;\s*margin: 20px 0;"', 'style="font-family: \'Archivo\', sans-serif; font-size: 110px; font-weight: 900; color: var(--accent); line-height: 1; margin: 20px 0;"', content) # stat hook
content = re.sub(r'class="title-main"\s+style="font-size: \$\{globalTitleSize\}px;"', 'class="title-main"', content) # cover title
content = re.sub(r'class="brand-logo-img"\s+style="height: \$\{logoSize\}px;\s*display: \$\{showLogo \? \'block\' : \'none\'\};"', 'class="brand-logo-img" style="display: ${showLogo ? \'block\' : \'none\'};"', content) # logo style
content = re.sub(r'onclick="selectSlide\(\$\{idx\}\)"\s+class="cursor-pointer', 'class="', content) # remove redundant onclick from container

with open(index_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated public/index.html')


# 2. Update server.js
server_path = 'server.js'
with open(server_path, 'r', encoding='utf-8') as f:
    server = f.read()

# Update getIconHtml inline styles
server = server.replace('const styleAttr = `style=\"color: ${color}; filter: drop-shadow(0px 4px 10px rgba(230,193,90,0.3)); width: 64px; height: 64px; margin-bottom: 25px;\" class=\"icon-box\"`;',
                        'const styleAttr = `class=\"icon-box\"`;')
server = re.sub(r'stroke=\"\$\{color\}\"', 'stroke="var(--accent)"', server)

server = server.replace('style=\"position: absolute; right: 40px; bottom: 15%; color: ${color}; opacity: 0.6; z-index: 10;\"',
                        'style=\"position: absolute; right: 40px; bottom: 15%; color: var(--accent); opacity: 0.6; z-index: 10;\"')

# Wrap rendering loop in try-finally and remove executablePath
server_render = r'''    const baseTemplatePath = path.resolve('templates/base_render.html');
    const templateStr = fs.readFileSync(baseTemplatePath, 'utf-8');

    let browser;
    let page;
    try {
      browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--allow-file-access-from-files']
      });

      page = await browser.newPage();
      await page.setViewport({ width: dimensions.width, height: dimensions.height, deviceScaleFactor: 2 });

      const pdfDoc = await PDFDocument.create();
      const timestamp = Date.now();'''

server = re.sub(r'    const baseTemplatePath = path\.resolve\(\'templates/base_render\.html\'\);\n    const templateStr = fs\.readFileSync\(baseTemplatePath, \'utf-8\'\);\n\n    const browser = await puppeteer\.launch\(\{\n      headless: true,\n      executablePath: \'C:\\\\Program Files\\\\Google\\\\Chrome\\\\Application\\\\chrome\.exe\',\n      args: \[\'--no-sandbox\', \'--disable-setuid-sandbox\', \'--allow-file-access-from-files\'\]\n    \}\);\n\n    const page = await browser\.newPage\(\);\n    await page\.setViewport\(\{ width: dimensions\.width, height: dimensions\.height, deviceScaleFactor: 2 \}\);\n\n    const pdfDoc = await PDFDocument\.create\(\);\n    const timestamp = Date\.now\(\);', server_render, server)

# Wait conditions
server = server.replace('''      await page.setContent(injectedHtml, { waitUntil: 'domcontentloaded', url: 'http://localhost:3000' });
      await page.evaluateHandle(() => document.fonts.ready); // CRITICAL: Wait for Google Fonts!''',
'''      await page.setContent(injectedHtml, { waitUntil: 'networkidle0', url: 'http://localhost:3000' });
      await page.evaluateHandle(() => document.fonts.ready); // CRITICAL: Wait for Google Fonts!
      await page.evaluateHandle(() => Promise.all(Array.from(document.images).filter(img => !img.complete).map(img => new Promise(resolve => { img.onload = img.onerror = resolve; }))));''')

# Close finally
server_end = r'''      fs.rmSync(slidePngPath, { force: true });
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
});'''

server = re.sub(r'      fs\.rmSync\(slidePngPath, \{ force: true \}\);\n    \}\n\n    await browser\.close\(\);\n\n    const pdfPath = path\.join\(tempDir, `output_deck_\$\{timestamp\}\.pdf`\);\n    const pdfBytes = await pdfDoc\.save\(\);\n    fs\.writeFileSync\(pdfPath, pdfBytes\);\n\n    res\.setHeader\(\'Content-Type\', \'application/pdf\'\);\n    res\.setHeader\(\'Content-Disposition\', `attachment; filename=\"fit_biblia_studio_pro_\$\{timestamp\}\.pdf\"`\);\n    return res\.sendFile\(pdfPath, \(\) => \{\n      fs\.rmSync\(pdfPath, \{ force: true \}\);\n    \}\);\n\n  \} catch \(error\) \{\n    console\.error\(\'Error generating slide deck:\', error\);\n    res\.status\(500\)\.json\(\{ error: \'Failed to generate slide deck\', details: error\.message \}\);\n  \}\n\}\);', server_end, server)

# Add titleSize and bodySize to replacements in server.js
server = server.replace('.replace(/\{\{CONTENT_WIDTH\}\}/g, contentWidth)',
                        '.replace(/{\{CONTENT_WIDTH\}\}/g, contentWidth)\n        .replace(/{\{TITLE_SIZE\}\}/g, titleSize)\n        .replace(/{\{BODY_SIZE\}\}/g, bodySize)')

# Also remove inline styles from contentBlock strings in server.js just like index.html
server = re.sub(r'style="font-size: \$\{titleSize\}px;\s*color: #E8DFC9;\s*text-transform: uppercase;"', '', server)
server = re.sub(r'style="font-size: \$\{bodySize\}px;\s*margin-top: 20px;"', 'style="margin-top: 20px;"', server)
server = re.sub(r'style="font-size: \$\{titleSize\}px;\s*font-family: \'Archivo\', sans-serif;\s*color: #E8DFC9;\s*text-transform: uppercase;\s*margin-bottom: 20px;"', 'style="font-family: \'Archivo\', sans-serif; color: #E8DFC9; text-transform: uppercase; margin-bottom: 20px; font-size: var(--title-size);"', server) # inner slide
server = re.sub(r'style="font-size: \$\{bodySize\}px;"', '', server) # inner body, myth body
server = re.sub(r'style="font-size: \$\{titleSize\}px;"', 'style="font-size: var(--title-size);"', server) # myth title
server = re.sub(r'style="font-family: \'Archivo\', sans-serif;\s*font-size: \$\{titleSize\}px;\s*font-weight: 800;\s*color: #E8DFC9;\s*text-transform: uppercase;"', 'style="font-family: \'Archivo\', sans-serif; font-size: var(--title-size); font-weight: 800; color: #E8DFC9; text-transform: uppercase;"', server) # stat title
server = re.sub(r'style="font-family: \'Archivo\', sans-serif;\s*font-size: 110px;\s*font-weight: 900;\s*color: \$\{customAccent\};\s*line-height: 1;\s*margin: 20px 0;"', 'style="font-family: \'Archivo\', sans-serif; font-size: 110px; font-weight: 900; color: var(--accent); line-height: 1; margin: 20px 0;"', server) # stat hook
server = re.sub(r'class="title-main"\s+style="font-size: \$\{titleSize\}px;"', 'class="title-main"', server) # cover title

with open(server_path, 'w', encoding='utf-8') as f:
    f.write(server)
print('Updated server.js')

# 3. Update templates/base_render.html
base_path = 'templates/base_render.html'
with open(base_path, 'r', encoding='utf-8') as f:
    base = f.read()

base = base.replace('<div class="slide-container">', '<div class="slide-container" style="--title-size: {{TITLE_SIZE}}px; --body-size: {{BODY_SIZE}}px; --logo-size: {{LOGO_SIZE}}px; --accent: {{ACCENT_COLOR}};">')

base = re.sub(r'\.brand-logo-img\s*\{\s*height: \{\{LOGO_SIZE\}\}px;\s*object-fit: contain;\s*display: \{\{LOGO_DISPLAY\}\};\s*\}',
                 '.brand-logo-img {\n    height: var(--logo-size);\n    object-fit: contain;\n    display: {{LOGO_DISPLAY}};\n  }', base)

base = re.sub(r'\.icon-box\s*\{\s*width: 64px;\s*height: 64px;\s*margin-bottom: 25px;\s*color: \{\{ACCENT_COLOR\}\};\s*filter: drop-shadow\(0px 4px 10px rgba\(230, 193, 90, 0\.3\)\);\s*\}',
                 '.icon-box {\n    width: 64px;\n    height: 64px;\n    margin-bottom: 25px;\n    color: var(--accent);\n    filter: drop-shadow(0px 4px 10px rgba(230, 193, 90, 0.3));\n  }', base)

base = re.sub(r'\.title-main\s*\{\s*font-family: \'Archivo\', sans-serif;\s*font-weight: 900;',
                 '.title-main {\n    font-family: \'Archivo\', sans-serif;\n    font-size: var(--title-size);\n    font-weight: 900;', base)

base = re.sub(r'\.body-text\s*\{\s*line-height: 1\.6;\s*color: #C7BEAB;\s*\}',
                 '.body-text {\n    font-size: var(--body-size);\n    line-height: 1.6;\n    color: #C7BEAB;\n  }', base)

base = re.sub(r'(\.ig-action-bar\s*\{[^}]+)(color: \{\{ACCENT_COLOR\}\};)',
                 r'\1color: var(--accent);', base)

with open(base_path, 'w', encoding='utf-8') as f:
    f.write(base)
print('Updated templates/base_render.html')
