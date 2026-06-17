// Background service worker — Taglish Disinformation Detection System

chrome.runtime.onInstalled.addListener(() => {
  // Set enabled by default on first install
  chrome.storage.local.get(['veriphi_enabled'], (result) => {
    if (result.veriphi_enabled === undefined) {
      chrome.storage.local.set({ veriphi_enabled: true });
    }
  });
  console.log('Taglish Disinformation Detection System initialized.');
});
