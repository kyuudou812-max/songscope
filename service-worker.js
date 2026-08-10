/* SongScope service worker — Phase F1.
 * 録音・解析結果は IndexedDB にあり、ここでは扱わない。外部通信も行わない。
 * 変更頻度の高いアプリ資産は network-first、アイコン等は cache-first。
 */
const CACHE = 'songscope-v0.2.0-phaseF1-20260810-f1-01';
const BUILD_ID = '20260810-f1-01';
const SHELL = [
  './',
  './index.html',
  './styles.css',
  './app.js?v=' + BUILD_ID,
  './audio-analysis-worker.js?v=' + BUILD_ID,
  './alignment-worker.js?v=' + BUILD_ID,
  './zip.js',
  './manifest.json',
  './icon-180.png',
  './icon-192.png',
  './icon-512.png'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
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
    p.endsWith('/styles.css') || p.endsWith('/manifest.json') || p.endsWith('/service-worker.js');
}

async function networkFirst(req) {
  const cache = await caches.open(CACHE);
  try {
    const res = await fetch(req, { cache: 'no-store' });
    if (res && res.status === 200 && res.type === 'basic') cache.put(req, res.clone()).catch(() => {});
    return res;
  } catch (err) {
    const hit = await cache.match(req);
    if (hit) return hit;
    if (req.mode === 'navigate') {
      const fallback = await cache.match('./index.html');
      if (fallback) return fallback;
    }
    throw err;
  }
}

async function cacheFirst(req) {
  const cache = await caches.open(CACHE);
  const hit = await cache.match(req);
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
