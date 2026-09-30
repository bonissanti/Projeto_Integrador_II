/*
  a11y.js
  High-contrast toggle. Loaded on every page via base.html, so this
  runs regardless of which template extends base.html.
*/
(function () {
  const STORAGE_KEY = 'a11y-high-contrast';

  function applyContrast(enabled) {
    document.body.classList.toggle('high-contrast', enabled);
    const btn = document.getElementById('a11y-toggle-btn');
    if (btn) {
      btn.setAttribute('aria-pressed', String(enabled));
      const label = btn.querySelector('.a11y-toggle-label');
      if (label) {
        label.textContent = enabled ? 'Contraste normal' : 'Alto contraste';
      }
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    const saved = localStorage.getItem(STORAGE_KEY) === 'true';
    applyContrast(saved);

    const btn = document.getElementById('a11y-toggle-btn');
    if (!btn) return;

    btn.addEventListener('click', function () {
      const isEnabled = !document.body.classList.contains('high-contrast');
      applyContrast(isEnabled);
      localStorage.setItem(STORAGE_KEY, String(isEnabled));
    });
  });
})();
