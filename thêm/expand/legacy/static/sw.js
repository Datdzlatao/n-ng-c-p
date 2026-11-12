/**
 * ============================================================
 *  SERVICE WORKER — Điểm Danh STEM Pro
 *  v2.0 — Offline Cache + Fetch Interceptor + Push Notifications
 * ============================================================
 */

const CACHE_NAME       = 'stem-pro-v2';
const RUNTIME_CACHE    = 'stem-runtime-v2';
const PUSH_BADGE_URL   = '/static/icons/badge-96.png';
const API_TIMEOUT_MS   = 6000;

// ── Static assets to cache on install (App Shell) ───────────
const PRECACHE_URLS = [
  '/',
  '/static/index.html',
  '/static/manifest.json',
  // External fonts & libraries (CDN) — cached at runtime on first fetch
];

// ── API routes that should ALWAYS go network-first ──────────
const NETWORK_FIRST_PATTERNS = [
  /\/api\/events/,     // SSE stream — never cache
  /\/api\/logs/,
  /\/api\/violations/,
  /\/api\/stats/,
  /\/api\/report/,
];

// ── Static assets → cache-first ─────────────────────────────
const CACHE_FIRST_PATTERNS = [
  /\/static\//,
  /fonts\.googleapis\.com/,
  /fonts\.gstatic\.com/,
  /cdn\.jsdelivr\.net/,
];

// ────────────────────────────────────────────────────────────
//  INSTALL — Pre-cache App Shell
// ────────────────────────────────────────────────────────────
self.addEventListener('install', event => {
  console.log('[SW] Installing Service Worker v2...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[SW] Pre-caching app shell');
        // Gracefully handle missing files (e.g. optional icon PNGs)
        return Promise.allSettled(
          PRECACHE_URLS.map(url =>
            cache.add(url).catch(err => console.warn(`[SW] Cannot cache ${url}:`, err))
          )
        );
      })
      .then(() => {
        console.log('[SW] App shell cached. Skipping waiting...');
        return self.skipWaiting();
      })
  );
});

// ────────────────────────────────────────────────────────────
//  ACTIVATE — Clean old caches & claim clients
// ────────────────────────────────────────────────────────────
self.addEventListener('activate', event => {
  console.log('[SW] Activating new Service Worker...');
  const keepCaches = [CACHE_NAME, RUNTIME_CACHE];

  event.waitUntil(
    caches.keys()
      .then(cacheNames =>
        Promise.all(
          cacheNames
            .filter(name => !keepCaches.includes(name))
            .map(name => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        )
      )
      .then(() => self.clients.claim())
      .then(() => console.log('[SW] Service Worker activated & claiming clients.'))
  );
});

// ────────────────────────────────────────────────────────────
//  FETCH — Interceptor Strategy Router
// ────────────────────────────────────────────────────────────
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // 1. Skip non-GET requests (POST/PUT/DELETE → always go to network)
  if (request.method !== 'GET') return;

  // 2. Skip chrome-extension or non-http schemes
  if (!url.protocol.startsWith('http')) return;

  // 3. SSE stream — bypass SW completely
  if (NETWORK_FIRST_PATTERNS.some(p => p.test(url.pathname))) {
    event.respondWith(networkFirst(request));
    return;
  }

  // 4. Static assets — cache first
  if (CACHE_FIRST_PATTERNS.some(p => p.test(url.href))) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // 5. Default — stale-while-revalidate (hybrid)
  event.respondWith(staleWhileRevalidate(request));
});

// ────────────────────────────────────────────────────────────
//  Cache Strategies
// ────────────────────────────────────────────────────────────

/** Network-first with timeout fallback to cache */
async function networkFirst(request) {
  const networkPromise = fetchWithTimeout(request, API_TIMEOUT_MS);
  try {
    const response = await networkPromise;
    if (response && response.ok) {
      // Only cache non-SSE JSON responses
      const ct = response.headers.get('content-type') || '';
      if (ct.includes('application/json') || ct.includes('text/html')) {
        const cache = await caches.open(RUNTIME_CACHE);
        cache.put(request, response.clone());
      }
    }
    return response;
  } catch (err) {
    console.warn('[SW] Network failed, serving from cache:', request.url);
    const cached = await caches.match(request);
    return cached || offlineFallbackResponse(request);
  }
}

/** Cache-first with network fallback */
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response && response.ok) {
      const cache = await caches.open(RUNTIME_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    return offlineFallbackResponse(request);
  }
}

/** Stale-while-revalidate: serve cache immediately, update in background */
async function staleWhileRevalidate(request) {
  const cache      = await caches.open(RUNTIME_CACHE);
  const cached     = await cache.match(request);
  const networkReq = fetch(request).then(response => {
    if (response && response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  }).catch(() => null);

  return cached || networkReq || offlineFallbackResponse(request);
}

/** Fetch with AbortController timeout */
function fetchWithTimeout(request, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  return fetch(request, { signal: controller.signal })
    .finally(() => clearTimeout(timer));
}

/** Offline fallback response */
function offlineFallbackResponse(request) {
  const url = new URL(request.url);
  const ct  = request.headers.get('accept') || '';

  if (ct.includes('text/html') || url.pathname === '/') {
    return caches.match('/') || new Response(
      `<!DOCTYPE html>
      <html lang="vi">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Điểm Danh STEM – Offline</title>
        <style>
          body { background:#0d1117; color:#c9d1d9; font-family:sans-serif;
                 display:flex; align-items:center; justify-content:center;
                 min-height:100vh; flex-direction:column; gap:16px; text-align:center; }
          .icon { font-size:4rem; }
          h1 { font-size:1.4rem; color:#f0f6fc; }
          p { color:#8b949e; font-size:0.9rem; max-width:280px; }
          button { margin-top:12px; padding:10px 24px; background:#238636;
                   color:#fff; border:none; border-radius:8px; font-size:1rem;
                   cursor:pointer; }
        </style>
      </head>
      <body>
        <div class="icon">📡</div>
        <h1>Đang offline</h1>
        <p>Không có kết nối mạng. Dữ liệu đã lưu vẫn hiển thị khi kết nối lại.</p>
        <button onclick="location.reload()">Thử lại</button>
      </body>
      </html>`,
      { headers: { 'Content-Type': 'text/html; charset=utf-8' } }
    );
  }

  if (ct.includes('application/json')) {
    return new Response(
      JSON.stringify({ error: 'offline', message: 'Không có kết nối mạng' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }

  return new Response('Offline', { status: 503 });
}

// ────────────────────────────────────────────────────────────
//  PUSH NOTIFICATIONS
// ────────────────────────────────────────────────────────────
self.addEventListener('push', event => {
  console.log('[SW] Push notification received');

  let payload = { title: 'Điểm Danh STEM', body: 'Có thông báo mới!', type: 'info' };

  try {
    if (event.data) {
      payload = { ...payload, ...event.data.json() };
    }
  } catch (e) {
    if (event.data) payload.body = event.data.text();
  }

  const { title, body, type, studentName, timestamp, photoUrl } = payload;

  const iconMap = {
    success   : '/static/icons/icon-192.png',
    violation : '/static/icons/icon-violation.png',
    stranger  : '/static/icons/icon-stranger.png',
    info      : '/static/icons/icon-192.png',
  };

  const tagMap = {
    success   : 'stem-checkin',
    violation : 'stem-violation',
    stranger  : 'stem-stranger',
    info      : 'stem-info',
  };

  const options = {
    body,
    icon        : iconMap[type] || iconMap.info,
    badge       : PUSH_BADGE_URL,
    tag         : tagMap[type] || 'stem-general',
    renotify    : true,
    requireInteraction: type === 'violation' || type === 'stranger',
    timestamp   : timestamp ? new Date(timestamp).getTime() : Date.now(),
    vibrate     : type === 'violation' ? [300, 100, 300, 100, 300] : [200, 100, 200],
    data        : { url: type === 'violation' ? '/#violations' : '/', photoUrl, type },
    actions     : type === 'violation'
      ? [
          { action: 'view',    title: '🔍 Xem Ảnh'   },
          { action: 'dismiss', title: '✓ Đã Xem'     },
        ]
      : [
          { action: 'open',    title: '📋 Mở Dashboard' },
        ],
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// ────────────────────────────────────────────────────────────
//  NOTIFICATION CLICK
// ────────────────────────────────────────────────────────────
self.addEventListener('notificationclick', event => {
  event.notification.close();
  const { action } = event;
  const { url, photoUrl } = event.notification.data || {};

  let targetUrl = '/';

  if (action === 'view' && photoUrl) {
    targetUrl = photoUrl;
  } else if (action === 'open' || !action) {
    targetUrl = url || '/';
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(windowClients => {
        // If a window is already open, focus & navigate it
        for (const client of windowClients) {
          if (client.url.includes(self.location.origin) && 'focus' in client) {
            client.navigate(targetUrl);
            return client.focus();
          }
        }
        // Otherwise open a new window
        if (clients.openWindow) return clients.openWindow(targetUrl);
      })
  );
});

// ────────────────────────────────────────────────────────────
//  BACKGROUND SYNC — Queue offline actions
// ────────────────────────────────────────────────────────────
self.addEventListener('sync', event => {
  console.log('[SW] Background sync event:', event.tag);
  if (event.tag === 'sync-offline-logs') {
    event.waitUntil(syncOfflineLogs());
  }
});

async function syncOfflineLogs() {
  try {
    const keys  = await caches.keys();
    console.log('[SW] Syncing offline logs to server...');
    // Notify open tabs that sync is happening
    const allClients = await clients.matchAll({ type: 'window' });
    for (const client of allClients) {
      client.postMessage({ type: 'SYNC_STARTED' });
    }
    // Signal complete
    for (const client of allClients) {
      client.postMessage({ type: 'SYNC_DONE' });
    }
  } catch (err) {
    console.error('[SW] Sync failed:', err);
  }
}

// ────────────────────────────────────────────────────────────
//  MESSAGE — Communication with main thread
// ────────────────────────────────────────────────────────────
self.addEventListener('message', event => {
  const { type, payload } = event.data || {};

  if (type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (type === 'CACHE_VIOLATION_PHOTO' && payload?.url) {
    caches.open(RUNTIME_CACHE).then(cache => cache.add(payload.url));
  }

  if (type === 'CLEAR_CACHE') {
    caches.delete(CACHE_NAME).then(() => {
      event.ports?.[0]?.postMessage({ success: true });
    });
  }
});

console.log('[SW] Service Worker script loaded — Điểm Danh STEM Pro v2.0');
