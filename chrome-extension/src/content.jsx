import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import tailwindStyles from './index.css?inline';

(function injectTaglish() {
  // Prevent duplicate injections
  if (document.getElementById('taglish-root')) return;

  // ── Gate: only mount if the extension is enabled ──────────────────────────
  // Checking storage HERE (before mounting React) is more reliable than
  // checking it inside App.jsx state — no async race, no false renders.
  chrome.storage.local.get(['veriphi_enabled'], (result) => {
    // Default to enabled on first install (background.js sets it, but be safe)
    if (result.veriphi_enabled === false) {
      console.log('[Taglish] Extension is OFF — skipping injection.');
      return;
    }

    // 1. Create host element
    const rootDiv = document.createElement('div');
    rootDiv.id = 'taglish-root';
    rootDiv.style.position = 'fixed';
    rootDiv.style.top = '0';
    rootDiv.style.left = '0';
    rootDiv.style.width = '100vw';
    rootDiv.style.height = '100vh';
    rootDiv.style.zIndex = '2147483647';
    rootDiv.style.pointerEvents = 'none';

    // 2. Attach Shadow DOM (isolates styles from the host page)
    const shadow = rootDiv.attachShadow({ mode: 'open' });

    // 3. Inject Tailwind CSS
    const styleSheet = document.createElement('style');
    styleSheet.textContent = tailwindStyles;
    shadow.appendChild(styleSheet);

    const scrollbarStyle = document.createElement('style');
    scrollbarStyle.textContent = `
      ::-webkit-scrollbar { width: 4px; }
      ::-webkit-scrollbar-track { background: rgba(15,23,42,0.5); }
      ::-webkit-scrollbar-thumb { background: #22c55e; border-radius: 2px; }
    `;
    shadow.appendChild(scrollbarStyle);

    // 4. Mount point for React
    const mountPoint = document.createElement('div');
    shadow.appendChild(mountPoint);

    // 5. Append host to page
    document.body.appendChild(rootDiv);

    // 6. Render React app
    const root = createRoot(mountPoint);
    root.render(
      <React.StrictMode>
        <App />
      </React.StrictMode>
    );

    console.log('[Taglish] Detection System injected and active.');
  });
})();
