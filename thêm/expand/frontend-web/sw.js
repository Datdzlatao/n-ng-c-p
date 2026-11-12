/**
 * sw.js — EduSAMS Progressive Web App (PWA) Service Worker
 * Strategy:
 *  - Stale-While-Revalidate for Static Assets (HTML views, CSS, JS, fonts, icons)
 *  - Network-First for API requests (/api/v1/...)
 */

const CACHE_NAME = 'edusams-pwa-v2.1.0';

const PRECACHE_ASSETS = [
  '/',
  '/manifest.webmanifest',
  '/manifest.json',
  '/config.js',
  '/assets/icons/icon-192.png',
  '/assets/icons/icon-512.png',
  '/assets/icons/icon.svg',
  '/assets/css/biometric-scanner.css?v=2.3.0',
  '/assets/js/biometric-scanner.js?v=2.3.0',
  
  // App Shell & CSS
  '/app/index.html',
  '/app/css/app.css',
  '/app/css/theme.css',
  '/app/css/layout.css',
  '/app/css/components.css',
  '/app/css/views.css',
  '/app/css/modals.css',
  '/app/css/print.css',

  // Modals & Partials
  '/app/modals/modals.html',
  '/app/views/launchpad.html',
  '/app/views/students.html',
  '/app/views/attendance.html',
  '/app/views/homeroom.html',
  '/app/views/cameras.html',
  '/app/views/classes.html',
  '/app/views/members.html',
  '/app/views/disputes.html',
  '/app/views/leaves.html',
  '/app/views/join-requests.html',
  '/app/views/verify.html',
  '/app/views/config.html',
  '/app/views/platform-admin.html',
  '/app/views/account.html',
  '/app/views/my-attendance.html',
  '/app/views/my-leaves.html',
  '/app/views/my-disputes.html',

  // App Core & Modules
  '/app/js/app.js',
  '/app/js/core/config.js',
  '/app/js/core/state.js',
  '/app/js/core/helpers.js',
  '/app/js/core/toast.js',
  '/app/js/core/api.js',
  '/app/js/core/websocket.js',
  '/app/js/core/view-loader.js',
  '/app/js/core/navigation.js',
  '/app/js/modals/modal_manager.js',
  '/app/js/modals/faceid_scanner.js',
  '/app/js/views/launchpad.js',
  '/app/js/views/students.js',
  '/app/js/views/attendance.js',
  '/app/js/views/disputes.js',
  '/app/js/views/leaves.js',
  '/app/js/views/cameras.js',
  '/app/js/views/homeroom.js',
  '/app/js/views/classes.js',
  '/app/js/views/members.js',
  '/app/js/views/join_requests.js',
  '/app/js/views/verify.js',
  '/app/js/views/config.js',
  '/app/js/views/platform_admin.js',
  '/app/js/views/account.js',
  '/app/js/views/parent_student.js',
  '/app/js/views/export.js'
];

// ── 1. Install Event (Precache Core Assets) ─────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Pre-caching offline assets...');
      return cache.addAll(PRECACHE_ASSETS).catch((err) => {
        console.warn('[SW] Pre-cache partial failure (ignoring non-critical):', err);
      });
    }).then(() => self.skipWaiting())
  );
});

// ── 2. Activate Event (Clean Up Outdated Caches) ───────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log('[SW] Removing old cache:', key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// ── 3. Fetch Event ─────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Ignore non-GET requests or WebSocket handshakes
  if (req.method !== 'GET' || url.protocol.startsWith('ws')) {
    return;
  }

  // API Requests: Network-First Strategy
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/health/')) {
    event.respondWith(
      fetch(req)
        .then((response) => {
          // Clone and cache successful GET responses
          if (response.status === 200) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((c) => c.put(req, copy));
          }
          return response;
        })
        .catch(async () => {
          const cached = await caches.match(req);
          if (cached) return cached;
          return new Response(
            JSON.stringify({ error: 'offline', detail: 'Hệ thống đang hoạt động ngoại tuyến (Offline Mode).' }),
            { status: 503, headers: { 'Content-Type': 'application/json' } }
          );
        })
    );
    return;
  }

  // Static Assets (HTML, CSS, JS, Icons, Fonts): Stale-While-Revalidate
  event.respondWith(
    caches.match(req).then((cachedResponse) => {
      const fetchPromise = fetch(req)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, responseToCache));
          }
          return networkResponse;
        })
        .catch(() => {
          // If network fails and no cached response, fallback for navigation
          if (req.mode === 'navigate') {
            return caches.match('/app/index.html');
          }
        });

      return cachedResponse || fetchPromise;
    })
  );
});
