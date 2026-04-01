/**
 * Light/dark theme: respects prefers-color-scheme, persists choice in localStorage.
 */
(function () {
  const storageKey = "compliancehub-theme";
  const doc = document.documentElement;

  function getStored() {
    try {
      return localStorage.getItem(storageKey);
    } catch {
      return null;
    }
  }

  function apply(theme) {
    if (theme === "light" || theme === "dark") {
      doc.setAttribute("data-theme", theme);
    } else {
      doc.removeAttribute("data-theme");
    }
  }

  function initFromStorageOrMedia() {
    const stored = getStored();
    if (stored === "light" || stored === "dark") {
      apply(stored);
      return;
    }
    apply(null);
  }

  function toggle() {
    const current = doc.getAttribute("data-theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    let next;
    if (!current) {
      next = prefersDark ? "light" : "dark";
    } else {
      next = current === "dark" ? "light" : "dark";
    }
    try {
      localStorage.setItem(storageKey, next);
    } catch {
      /* ignore */
    }
    apply(next);
    updateToggleLabel(next);
  }

  function updateToggleLabel(theme) {
    const btn = document.getElementById("theme-toggle");
    if (!btn) return;
    const isDark = theme === "dark" || (!theme && window.matchMedia("(prefers-color-scheme: dark)").matches);
    btn.setAttribute("aria-label", isDark ? "Hellmodus aktivieren" : "Dunkelmodus aktivieren");
    btn.setAttribute("title", isDark ? "Hellmodus" : "Dunkelmodus");
  }

  window.addEventListener("DOMContentLoaded", function () {
    initFromStorageOrMedia();
    const stored = getStored();
    updateToggleLabel(stored === "light" || stored === "dark" ? stored : null);

    const btn = document.getElementById("theme-toggle");
    if (btn) btn.addEventListener("click", toggle);

    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
      if (!getStored()) {
        apply(null);
        updateToggleLabel(null);
      }
    });
  });
})();
