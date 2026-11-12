// app/js/modals/modal_manager.js — Modal Dialog Controller
// ── Modal helpers ─────────────────────────────────
function openModal(id)  { document.getElementById(id).classList.add('active'); }
function closeModal(id) { document.getElementById(id).classList.remove('active'); }



// Close modal on Escape key
if (typeof window !== 'undefined') {
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const activeModals = document.querySelectorAll('.modal-overlay.active');
      activeModals.forEach(m => m.classList.remove('active'));
    }
  });
}

export { openModal, closeModal };
