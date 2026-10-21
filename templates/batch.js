// batch.js — render a few stills for review (fast iteration loop)
// usage: node batch.js <film.html> <h|v> "1.2,3.6,9.2" <outdir>
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
  const vert = process.argv[3] === 'v';
  const times = (process.argv[4] || '1.2').split(',').map(Number);
  const dir = process.argv[5] || 'out/qa';
  fs.mkdirSync(dir, { recursive: true });

  const VW = vert ? 1080 : 1920, VH = vert ? 1920 : 1080;
  const browser = await puppeteer.launch({
    executablePath: BROWSER, headless: 'new',
    args: ['--allow-file-access-from-files', '--font-render-hinting=none',
           '--disable-lcd-text', '--hide-scrollbars', '--force-color-profile=srgb']
  });
  const page = await browser.newPage();
  await page.setViewport({ width: VW, height: VH, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.log('PAGEERROR:', e.message));
  page.on('console', m => { if (m.type() === 'error') console.log('CONSOLE:', m.text()); });

  const url = 'file:///' + path.resolve(html).replace(/\\/g, '/') + (vert ? '?v=1' : '');
  await page.goto(url, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await new Promise(r => setTimeout(r, 500));

  for (const t of times) {
    await page.evaluate(t => window.renderAt(t), t);
    await page.screenshot({ path: dir + '/' + (vert ? 'v_' : 'h_') + t.toFixed(2) + '.png' });
  }
  await browser.close();
  console.log('done ' + (vert ? 'V' : 'H') + ' ' + times.length + ' stills -> ' + dir);
})();
