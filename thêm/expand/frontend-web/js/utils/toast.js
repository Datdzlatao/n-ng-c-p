/**
 * js/utils/toast.js — Debounced & Limited Notification Toast System
 */
import { escHtml } from './helpers.js';

const toastRecentMap = new Map();
const TOAST_COOLDOWN_MS = 2500;
const MAX_TOASTS = 3;

/**
 * Display a toast notification with automatic cooldown & deduplication
 * @param {string} title 
 * @param {string} msg 
 * @param {'info' | 'success' | 'error' | 'warning'} type 
 */
export function toast(title, msg = '', type = 'info') {
  const now = Date.now();
  const toastKey = `${title}_${msg}_${type}`;

  if (toastRecentMap.has(toastKey) && (now - toastRecentMap.get(toastKey)) < TOAST_COOLDOWN_MS) {
    return;
  }
  toastRecentMap.set(toastKey, now);

  const container = document.getElementById('toastContainer');
  if (!container) return;

  const activeToasts = container.querySelectorAll('.toast');
  if (activeToasts.length >= MAX_TOASTS) {
    activeToasts[0].remove();
  }

  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `
    <div class="toast-title">${escHtml(title)}</div>
    ${msg ? `<div class="toast-msg">${escHtml(msg)}</div>` : ''}
  `;
  container.appendChild(el);

  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateX(20px)';
    el.style.transition = '0.3s ease-out';
    setTimeout(() => el.remove(), 300);
  }, 4000);
}

window.toast = toast;
