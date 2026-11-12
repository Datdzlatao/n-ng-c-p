// app/js/core/view-loader.js — Asynchronous View & Modal Loader with DOM Caching
const loadedViews = new Set();
let modalsLoaded = false;

export async function loadView(viewId) {
  if (document.getElementById(viewId)) {
    loadedViews.add(viewId);
    return true;
  }
  const viewName = viewId.replace('view-', '');
  try {
    const res = await fetch(`./views/${viewName}.html`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const html = await res.text();
    const content = document.getElementById('content');
    if (content) {
      content.insertAdjacentHTML('beforeend', html);
      loadedViews.add(viewId);
      return true;
    }
  } catch (err) {
    console.error(`[ViewLoader] Failed to load partial view: ${viewName}`, err);
  }
  return false;
}

export async function loadModals() {
  if (modalsLoaded) return true;
  const container = document.getElementById('modalsContainer');
  if (!container) return false;
  try {
    const res = await fetch('./modals/modals.html');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const html = await res.text();
    container.innerHTML = html;
    modalsLoaded = true;
    return true;
  } catch (err) {
    console.error('[ViewLoader] Failed to load modals.html', err);
    return false;
  }
}
