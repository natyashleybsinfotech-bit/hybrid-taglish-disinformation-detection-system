import React, { useState, useEffect } from 'react';
import { Power, ShieldCheck, ShieldOff } from 'lucide-react';

export default function Popup() {
  const [isEnabled, setIsEnabled] = useState(true);

  useEffect(() => {
    chrome.storage.local.get(['veriphi_enabled'], (result) => {
      if (result.veriphi_enabled !== undefined) {
        setIsEnabled(result.veriphi_enabled);
      }
    });
  }, []);

  const toggle = () => {
    const newState = !isEnabled;
    setIsEnabled(newState);
    // Save state first, THEN reload the active tab so the page starts
    // fresh with the correct veriphi_enabled value already in storage.
    chrome.storage.local.set({ veriphi_enabled: newState }, () => {
      chrome.tabs.query({ active: true, lastFocusedWindow: true }, (tabs) => {
        if (tabs && tabs[0] && tabs[0].id) {
          chrome.tabs.reload(tabs[0].id);
        }
      });
    });
  };

  return (
    <div className="w-[300px] bg-slate-950 flex flex-col text-white border border-slate-800 font-mono">

      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800 bg-slate-900">
        <ShieldCheck size={16} className="text-green-400 shrink-0" />
        <div>
          <div className="text-[9px] font-bold tracking-[0.15em] text-slate-300 uppercase leading-tight">
            Taglish Disinformation
          </div>
          <div className="text-[9px] font-bold tracking-[0.15em] text-slate-300 uppercase leading-tight">
            Detection System
          </div>
        </div>
      </div>

      {/* Status display */}
      <div className={`flex items-center justify-center gap-3 py-5 transition-all duration-300 ${
        isEnabled ? 'bg-green-950/30' : 'bg-slate-900/50'
      }`}>
        <div className={`rounded-full p-3 transition-all duration-300 ${
          isEnabled
            ? 'bg-green-500/20 shadow-[0_0_20px_rgba(34,197,94,0.4)]'
            : 'bg-slate-800'
        }`}>
          {isEnabled
            ? <ShieldCheck size={28} className="text-green-400" />
            : <ShieldOff size={28} className="text-slate-500" />
          }
        </div>
        <div className="flex flex-col">
          <span className={`text-base font-extrabold tracking-widest uppercase ${
            isEnabled ? 'text-green-400' : 'text-slate-500'
          }`}>
            {isEnabled ? 'ACTIVE' : 'DISABLED'}
          </span>
          <span className="text-[10px] text-slate-500 mt-0.5">
            {isEnabled ? 'Scanning posts on this page' : 'Extension is turned off'}
          </span>
        </div>
      </div>

      {/* Toggle button */}
      <div className="flex flex-col items-center gap-2 px-5 py-4 border-t border-slate-800">
        <button
          onClick={toggle}
          className={`w-full flex items-center justify-center gap-2.5 py-3 rounded-lg font-bold text-sm tracking-wider uppercase transition-all duration-200 cursor-pointer border ${
            isEnabled
              ? 'bg-red-900/30 border-red-500/50 text-red-400 hover:bg-red-900/50 hover:border-red-400'
              : 'bg-green-900/30 border-green-500/50 text-green-400 hover:bg-green-900/50 hover:border-green-400'
          }`}
        >
          <Power size={16} />
          {isEnabled ? 'Turn Off' : 'Turn On'}
        </button>
        <p className="text-[9px] text-slate-600 text-center leading-relaxed">
          {isEnabled
            ? 'Turning off will reload the page and remove all scan buttons.'
            : 'Turning on will reload the page and inject scan buttons into posts.'
          }
        </p>
      </div>

      {/* Footer reminder */}
      <div className="px-4 py-2.5 border-t border-slate-800 bg-slate-900/60">
        <p className="text-[9px] text-slate-500 text-center leading-relaxed">
          🔍 Always fact-check before sharing any content online.
        </p>
      </div>

    </div>
  );
}
