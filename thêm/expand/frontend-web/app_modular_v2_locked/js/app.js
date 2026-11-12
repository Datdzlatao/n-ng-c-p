// app/js/app.js — EduSAMS Dashboard Master Entry Point (ES Module)
import * as config from './core/config.js';
import * as state from './core/state.js';
import * as helpers from './core/helpers.js';
import * as toastModule from './core/toast.js';
import * as apiModule from './core/api.js';
import * as wsModule from './core/websocket.js';
import * as viewLoader from './core/view-loader.js';
import * as navModule from './core/navigation.js';
import * as modalManager from './modals/modal_manager.js';
import * as faceidScanner from './modals/faceid_scanner.js';

import * as launchpad from './views/launchpad.js';
import * as students from './views/students.js';
import * as attendance from './views/attendance.js';
import * as disputes from './views/disputes.js';
import * as leaves from './views/leaves.js';
import * as cameras from './views/cameras.js';
import * as homeroom from './views/homeroom.js';
import * as classes from './views/classes.js';
import * as members from './views/members.js';
import * as joinRequests from './views/join_requests.js';
import * as verify from './views/verify.js';
import * as configView from './views/config.js';
import * as platformAdmin from './views/platform_admin.js';
import * as account from './views/account.js';
import * as parentStudent from './views/parent_student.js';
import * as exportView from './views/export.js';

// ── Bind All Handlers to Window for 100% HTML Inline Attribute Compatibility ──
const modules = [
  config, state, helpers, toastModule, apiModule, wsModule, viewLoader,
  navModule, modalManager, faceidScanner, launchpad, students, attendance,
  disputes, leaves, cameras, homeroom, classes, members, joinRequests,
  verify, configView, platformAdmin, account, parentStudent, exportView
];

for (const mod of modules) {
  Object.assign(window, mod);
}

// ── Service Worker & PWA Support ──
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then(reg => {
        console.log('[PWA] Service Worker registered with scope:', reg.scope);
      })
      .catch(err => {
        console.warn('[PWA] Service Worker registration failed:', err);
      });
  });
}

// Handle online / offline network state
window.addEventListener('online', () => {
  if (typeof updateConnectionBanner === 'function') updateConnectionBanner(true);
});
window.addEventListener('offline', () => {
  if (typeof updateConnectionBanner === 'function') updateConnectionBanner(false);
});

// ── App Initialization ──
document.addEventListener('DOMContentLoaded', async () => {
  console.log('🎓 EduSAMS Modular Dashboard initializing...');
  
  // Preload modals and default launchpad view
  await Promise.all([
    viewLoader.loadModals(),
    viewLoader.loadView('view-launchpad')
  ]);

  // Boot application auth and data loaders
  if (typeof bootApp === 'function') {
    bootApp();
  }
});
