/**
 * js/utils/modal.js — Modal Overlay Helpers
 */

/**
 * Open modal by element ID
 * @param {string} id 
 */
export function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.add('active');
  }
}

/**
 * Close modal by element ID
 * @param {string} id 
 */
export function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.remove('active');
  }
}

window.openModal = openModal;
window.closeModal = closeModal;
