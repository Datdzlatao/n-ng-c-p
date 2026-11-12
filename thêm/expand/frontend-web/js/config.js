/**
 * js/config.js — Client Application Configuration
 */

const isDevFrontendPort = ['5173', '3000'].includes(window.location.port);
const isLocalHostname = ['localhost', '127.0.0.1', '0.0.0.0'].includes(window.location.hostname);
const isLanHostname = /^(192\.168\.|10\.|172\.(1[6-9]|2\d|3[01])\.)/.test(window.location.hostname);
const isSeparateDevServer = isDevFrontendPort && (isLocalHostname || isLanHostname);

export const STEM_CONFIG = {
  API_BASE: isSeparateDevServer
    ? `http://${window.location.hostname}:8000`
    : '',

  WS_BASE: isSeparateDevServer
    ? `ws://${window.location.hostname}:8000`
    : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`,

  APP_NAME: 'Điểm Danh STEM',
  APP_VERSION: '1.0.0',
};

export const AUTH_KEY = 'stem_auth_token';
export const ADMIN_TOKEN_KEY = 'stem_admin_token';
export const REFRESH_TOKEN_KEY = 'stem_refresh_token';
export const SCHOOL_ID_KEY = 'stem_school_id';

// Expose globally for backwards compatibility
window.STEM_CONFIG = STEM_CONFIG;
window.AUTH_KEY = AUTH_KEY;
window.ADMIN_TOKEN_KEY = ADMIN_TOKEN_KEY;
