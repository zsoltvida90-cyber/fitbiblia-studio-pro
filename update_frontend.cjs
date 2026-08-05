const fs = require('fs');
const path = require('path');

const indexPath = path.resolve('public/index.html');
let content = fs.readFileSync(indexPath, 'utf-8');

// 1. Add Project Manager panel to the left sidebar (before Global Settings)
const projectPanelHTML = `
        <div class="glass-panel p-6 mb-6 relative overflow-hidden">
          <div class="absolute -top-10 -right-10 w-32 h-32 bg-gold/10 rounded-full blur-3xl"></div>
          <h2 class="text-xl font-bold font-archivo tracking-widest text-gold mb-4 flex items-center gap-2">
            <i data-lucide="folder-kanban" class="w-5 h-5"></i>
            MENTETT PROJEKTEK
          </h2>
          <div class="space-y-4 relative z-10">
            <div>
              <label class="block text-xs font-mono text-grey mb-1">Új projekt mentése</label>
              <div class="flex gap-2">
                <input type="text" id="projectName" class="ig-input flex-1" placeholder="Projekt neve...">
                <button id="saveProjectBtn" class="bg-gold text-dark font-bold px-4 py-2 rounded-lg hover:bg-yellow-400 transition">Mentés</button>
              </div>
            </div>
            <div>
              <label class="block text-xs font-mono text-grey mb-1">Projekt betöltése</label>
              <select id="projectSelect" class="ig-input w-full">
                <option value="">Válassz projektet...</option>
              </select>
            </div>
          </div>
        </div>
`;

content = content.replace(/<div class="glass-panel p-6 mb-6 relative overflow-hidden">\s*<div class="absolute -top-10 -right-10 w-32 h-32 bg-gold\/10 rounded-full blur-3xl"><\/div>\s*<h2 class="text-xl font-bold font-archivo tracking-widest text-gold mb-4 flex items-center gap-2">\s*<i data-lucide="settings" class="w-5 h-5"><\/i>\s*GLOBA\s*BEA/, projectPanelHTML + '\n        <div class="glass-panel p-6 mb-6 relative overflow-hidden">\n          <div class="absolute -top-10 -right-10 w-32 h-32 bg-gold/10 rounded-full blur-3xl"></div>\n          <h2 class="text-xl font-bold font-archivo tracking-widest text-gold mb-4 flex items-center gap-2">\n            <i data-lucide="settings" class="w-5 h-5"></i>\n            GLOBÁLIS BEÁLLÍTÁSOK');

// If the regex replacement didn't work due to encoding or small differences, let's just do a string replace on the headline
if (!content.includes('MENTETT PROJEKTEK')) {
  content = content.replace('<h2 class="text-xl font-bold font-archivo tracking-widest text-gold mb-4 flex items-center gap-2">\n            <i data-lucide="settings"', projectPanelHTML + '        <h2 class="text-xl font-bold font-archivo tracking-widest text-gold mb-4 flex items-center gap-2">\n            <i data-lucide="settings"');
}


// 2. Change Generate Button
content = content.replace('ÖSSZES SLIDE ÉS PDF GENERÁLÁSA', 'ÖSSZES SLIDE EXPORTÁLÁSA (ZIP)');


// 3. Add Project Management JS Logic
const projectLogic = `
    // --- Project Management Logic ---
    async function fetchProjects() {
      try {
        const res = await fetch('/api/projects');
        const data = await res.json();
        const select = document.getElementById('projectSelect');
        select.innerHTML = '<option value="">Válassz projektet...</option>';
        if (data.projects) {
          data.projects.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = p.name;
            select.appendChild(opt);
          });
        }
      } catch (err) {
        console.error('Failed to load projects', err);
      }
    }

    document.getElementById('saveProjectBtn').addEventListener('click', async () => {
      const name = document.getElementById('projectName').value.trim();
      if (!name) return alert('Kérlek add meg a projekt nevét!');
      
      syncActiveSlideFromForm();
      const btn = document.getElementById('saveProjectBtn');
      btn.textContent = '...';
      
      try {
        const res = await fetch('/api/projects', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, deck: slideDeck })
        });
        if (res.ok) {
          document.getElementById('projectName').value = '';
          alert('Projekt sikeresen mentve!');
          await fetchProjects();
        } else {
          alert('Hiba a mentés során.');
        }
      } catch (err) {
        console.error(err);
        alert('Hiba a mentés során.');
      } finally {
        btn.textContent = 'Mentés';
      }
    });

    document.getElementById('projectSelect').addEventListener('change', async (e) => {
      const id = e.target.value;
      if (!id) return;
      try {
        const res = await fetch(\`/api/projects/\${id}\`);
        if (res.ok) {
          const data = await res.json();
          if (data.deck && Array.isArray(data.deck)) {
            slideDeck = data.deck;
            activeSlideIndex = 0;
            renderUI();
            selectSlide(0);
            updatePreview();
            alert('Projekt betöltve!');
          }
        }
      } catch (err) {
        console.error('Failed to load project details', err);
      }
    });
    // --------------------------------
`;

content = content.replace('// Form Change Listeners for Instant Live Updating', projectLogic + '\n    // Form Change Listeners for Instant Live Updating');


// 4. Update the Generator handler
content = content.replace(/'ÖSSZES SLIDE ÉS PDF RENDERELÉSE...'/g, "'ÖSSZES SLIDE EXPORTÁLÁSA (ZIP)...'");
content = content.replace(/fit_biblia_studio_pro_\$\{Date\.now\(\)\}\.pdf/g, 'fit_biblia_studio_pro_${Date.now()}.zip');
content = content.replace(/'ÖSSZES SLIDE ÉS PDF GENERÁLÁSA'/g, "'ÖSSZES SLIDE EXPORTÁLÁSA (ZIP)'");
content = content.replace(/\/api\/generate/g, '/api/export-batch');

// Add fetchProjects call to initial load
content = content.replace('loadPreferences();', 'loadPreferences();\n    fetchProjects();');

fs.writeFileSync(indexPath, content, 'utf-8');
console.log('Updated public/index.html');
