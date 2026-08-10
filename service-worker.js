/* SongScope service worker — Audit Remediation R0.
 * IndexedDBの証拠データは扱わない。アプリ資産のoffline fallbackのみ担当する。
 * install時にskipWaitingしない: 実行中ページと新workerのversion skewを避ける。
 */
const CACHE = 'songscope-v0.2.0-auditR0-20260810-r0-01';
const BUILD_ID = '20260810-r0-01';
const SHELL = [
  './',
  './index.html',
  './styles.css?v=' + BUILD_ID,
  './app.js?v=' + BUILD_ID,
  './audio-analysis-worker.js?v=' + BUILD_ID,
  './alignment-worker.js?v=' + BUILD_ID,
  './zip.js?v=' + BUILD_ID,
  './manifest.json',
  './icon-180.png',
  './icon-192.png',
  './icon-512.png'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function isMutableRequest(req, url) {
  if (req.mode === 'navigate') return true;
  const p = url.pathname;
  return p.endsWith('/index.html') || p.endsWith('/app.js') || p.endsWith('/audio-analysis-worker.js') || p.endsWith('/alignment-worker.js') ||
    p.endsWith('/styles.css') || p.endsWith('/zip.js') || p.endsWith('/manifest.json') || p.endsWith('/service-worker.js');
}

async function networkFirst(req) {
  const cache = await caches.open(CACHE);
  try {
    const res = await fetch(req, { cache: 'no-store' });
    if (res && res.status === 200 && res.type === 'basic') cache.put(req, res.clone()).catch(() => {});
    return res;
  } catch (err) {
    // HTML側のcache-busting queryとprecache keyがずれてもoffline fallbackできる。
    const hit = await cache.match(req, { ignoreSearch: true });
    if (hit) return hit;
    if (req.mode === 'navigate') {
      const fallback = await cache.match('./index.html', { ignoreSearch: true });
      if (fallback) return fallback;
    }
    throw err;
  }
}

async function cacheFirst(req) {
  const cache = await caches.open(CACHE);
  const hit = await cache.match(req, { ignoreSearch: true });
  if (hit) return hit;
  const res = await fetch(req);
  if (res && res.status === 200 && res.type === 'basic') cache.put(req, res.clone()).catch(() => {});
  return res;
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  e.respondWith(isMutableRequest(req, url) ? networkFirst(req) : cacheFirst(req));
});
