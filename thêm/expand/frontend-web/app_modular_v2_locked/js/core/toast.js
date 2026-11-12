// app/js/core/toast.js — Toast Notifications System
// ── Toast ─────────────────────────────────────────
function toast(title, msg, type='info') {
  const c  = document.getElementById('toast');
  const el = document.createElement('div');
  el.className = `toast-item ${type}`;
  el.innerHTML = `<div class="toast-title">${title}</div>${msg?`<div class="toast-msg">${msg}</div>`:''}`;
  c.appendChild(el);
  setTimeout(() => { el.style.opacity='0'; el.style.transition='.3s'; setTimeout(()=>el.remove(),300); }, 4000);
}



export { toast };
