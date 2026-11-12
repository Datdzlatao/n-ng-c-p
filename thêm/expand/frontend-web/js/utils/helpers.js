/**
 * js/utils/helpers.js — Helper Functions & Sanitization
 */

/**
 * Escape HTML to prevent DOM XSS vulnerabilities
 * @param {*} str 
 * @returns {string}
 */
export function escHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;');
}

window.escHtml = escHtml;
