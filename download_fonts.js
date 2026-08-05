import fs from 'fs';
import path from 'path';
import https from 'https';

const fonts = [
  {
    name: 'Archivo-Black.ttf',
    url: 'https://cdn.jsdelivr.net/fontsource/fonts/archivo-black@latest/latin-400-normal.ttf'
  },
  {
    name: 'Archivo-ExtraBold.ttf',
    url: 'https://cdn.jsdelivr.net/fontsource/fonts/archivo@latest/latin-800-normal.ttf'
  },
  {
    name: 'Fraunces-900Italic.ttf',
    url: 'https://cdn.jsdelivr.net/fontsource/fonts/fraunces@latest/latin-900-italic.ttf'
  },
  {
    name: 'IBMPlexMono-Medium.ttf',
    url: 'https://cdn.jsdelivr.net/fontsource/fonts/ibm-plex-mono@latest/latin-500-normal.ttf'
  },
  {
    name: 'IBMPlexMono-SemiBold.ttf',
    url: 'https://cdn.jsdelivr.net/fontsource/fonts/ibm-plex-mono@latest/latin-600-normal.ttf'
  },
  {
    name: 'Inter-Regular.ttf',
    url: 'https://cdn.jsdelivr.net/fontsource/fonts/inter@latest/latin-400-normal.ttf'
  },
  {
    name: 'Inter-SemiBold.ttf',
    url: 'https://cdn.jsdelivr.net/fontsource/fonts/inter@latest/latin-600-normal.ttf'
  },
  {
    name: 'Inter-Bold.ttf',
    url: 'https://cdn.jsdelivr.net/fontsource/fonts/inter@latest/latin-700-normal.ttf'
  }
];

const destDir = path.resolve('assets/fonts');
if (!fs.existsSync(destDir)) {
  fs.mkdirSync(destDir, { recursive: true });
}

function download(url, dest) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(dest);
    https.get(url, (response) => {
      if (response.statusCode === 302 || response.statusCode === 301) {
        return download(response.headers.location, dest).then(resolve).catch(reject);
      }
      if (response.statusCode !== 200) {
        return reject(new Error(`Failed to download ${url}: status code ${response.statusCode}`));
      }
      response.pipe(file);
      file.on('finish', () => {
        file.close(() => resolve());
      });
    }).on('error', (err) => {
      fs.unlink(dest, () => reject(err));
    });
  });
}

async function run() {
  console.log('Downloading fonts...');
  for (const f of fonts) {
    const target = path.join(destDir, f.name);
    console.log(`Downloading ${f.name}...`);
    try {
      await download(f.url, target);
      console.log(`Saved ${f.name}`);
    } catch (e) {
      console.error(`Error downloading ${f.name}:`, e.message);
    }
  }
  console.log('Fonts download complete.');
}

run();
