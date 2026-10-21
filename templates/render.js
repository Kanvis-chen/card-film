// render.js — drive headless Edge and shoot every frame of film.html
// usage: node render.js <film.html> <outdir> <h|v> [duration] [fps]
//
// env overrides:
//   PUPPETEER_CORE  path to puppeteer-core   (default: resolve from node_modules)
//   BROWSER         path to msedge / chrome  (default: auto-detect)
const path = require('path'), fs = require('fs');

function loadPuppeteer() {
  const cands = [
    process.env.PUPPETEER_CORE,
    path.join(__dirname, '..', 'node_modules', 'puppeteer-core'),
    'puppeteer-core',
  ].filter(Boolean);
  for (const c of cands) { try { return require(c); } catch (e) {} }
  console.error('puppeteer-core not found.\n  npm i puppeteer-core    (or set PUPPETEER_CORE=<path>)');
  process.exit(1);
}

function findBrowser() {
  if (process.env.BROWSER) return process.env.BROWSER;
  const cands = [
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
  ];
  for (const c of cands) if (fs.existsSync(c)) return c;
  console.error('no Edge/Chrome found — set BROWSER=<path to browser binary>');
  process.exit(1);
}

const puppeteer = loadPuppeteer();
const BROWSER = findBrowser();

(async () => {
  const html = process.argv[2] || 'film.html';
  const OUT  = process.argv[3] || 'out/frames_h';
  const vert = process.argv[4] === 'v';
  const DUR  = parseFloat(process.argv[5] || '15.10');
  const FPS  = parseInt(process.argv[6] || '60', 10);
  fs.mkdirSync(OUT, { recursive: true });

  const VW = vert ? 1080 : 1920, VH = vert ? 1920 : 1080;
  const browser = await puppeteer.launch({
    executablePath: BROWSER, headless: 'new',
    args: ['--allow-file-access-from-files', '--font-render-hinting=none',
           '--disable-lcd-text', '--hide-scrollbars', '--disable-gpu-vsync',
           '--force-color-profile=srgb']
  });
  const page = await browser.newPage();
  await page.setViewport({ width: VW, height: VH, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.log('PAGEERROR:', e.message));
  page.on('console', m => { if (m.type() === 'error') console.log('CONSOLE:', m.text()); });

  const url = 'file:///' + path.resolve(html).replace(/\\/g, '/') + (vert ? '?v=1' : '');
  await page.goto(url, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await new Promise(r => setTimeout(r, 600));

  const N = Math.round(DUR * FPS), t0 = Date.now();
  for (let i = 0; i < N; i++) {
    await page.evaluate(t => window.renderAt(t), i / FPS);
    await page.screenshot({ path: OUT + '/f_' + String(i).padStart(4, '0') + '.jpg', type: 'jpeg', quality: 94 });
    if (i % 120 === 0) console.log('frame', i, '/', N, ((Date.now() - t0) / 1000).toFixed(1) + 's');
  }
  await browser.close();
  console.log('DONE ' + (vert ? 'V' : 'H') + ' ' + N + ' frames in ' + ((Date.now() - t0) / 1000).toFixed(1) + 's');
})();
