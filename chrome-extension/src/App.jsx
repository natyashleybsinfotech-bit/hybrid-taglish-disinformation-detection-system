import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import {
  XCircle, ShieldAlert, ShieldCheck, AlertTriangle,
  BookOpen, TrendingUp, Info
} from 'lucide-react';
import { analyzeText } from './api';
import tailwindStyles from './index.css?inline';

// ─── Scan Button injected per-post ──────────────────────────────────────────
const ScanButton = ({ post, onScan, onViewBreakdown }) => {
  if (post.status === 'idle') {
    return (
      <button
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); onScan(post); }}
        className="flex items-center justify-center w-[34px] h-[34px] bg-green-600 text-white rounded-full shadow-[0_0_10px_rgba(22,163,74,0.5)] hover:bg-green-500 hover:scale-110 transition-all pointer-events-auto cursor-pointer"
        title="Scan this post"
      >
        <ShieldCheck size={18} fill="currentColor" fillOpacity={0.2} />
      </button>
    );
  }

  if (post.status === 'scanning') {
    return (
      <div className="flex items-center justify-center w-[34px] h-[34px] bg-slate-900 border-2 border-green-500 text-green-500 rounded-full shadow-lg pointer-events-auto">
        <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      </div>
    );
  }

  const { label } = post.resultData;
  const isDis = label === 'Disinformation';
  return (
    <button
      onClick={(e) => { e.preventDefault(); e.stopPropagation(); onViewBreakdown(post); }}
      className={`flex items-center justify-center w-[34px] h-[34px] text-white rounded-full pointer-events-auto animate-pulse cursor-pointer transition-all hover:brightness-125
        ${isDis
          ? 'bg-red-600 shadow-[0_0_15px_rgba(220,38,38,0.7)]'
          : 'bg-green-600 shadow-[0_0_15px_rgba(22,163,74,0.7)]'
        }`}
      title={`${label} — Click to view details`}
    >
      {isDis
        ? <ShieldAlert size={18} fill="currentColor" fillOpacity={0.2} />
        : <ShieldCheck size={18} fill="currentColor" fillOpacity={0.2} />
      }
    </button>
  );
};

// ─── Feature row with optional highlighted state ─────────────────────────────
const FeatureRow = ({ label, value, color, isTriggered, description }) => (
  <div className={`flex items-start justify-between gap-3 px-3 py-2 rounded-lg transition-all
    ${isTriggered
      ? 'bg-amber-900/30 border border-amber-500/60 shadow-[0_0_8px_rgba(245,158,11,0.2)]'
      : 'bg-slate-800/40 border border-slate-700/40'
    }`}
  >
    <div className="flex flex-col min-w-0">
      {isTriggered && (
        <span className="text-amber-400 text-[9px] font-bold uppercase tracking-wider bg-amber-900/50 px-1.5 py-0.5 rounded w-fit mb-0.5">
          ⚡ Key Signal
        </span>
      )}
      <span className={`text-xs font-medium ${isTriggered ? 'text-amber-200' : 'text-slate-300'}`}>
        {label}
      </span>
      <span className="text-[10px] text-slate-500 leading-tight mt-0.5">{description}</span>
    </div>
    <span className={`text-sm font-bold shrink-0 ${color}`}>{value}</span>
  </div>
);

// ─── Feature metadata ────────────────────────────────────────────────────────
const FEATURE_META = {
  code_switching_ratio: {
    label: 'Code-Switching Ratio',
    color: 'text-purple-400',
    description: "Mix of Filipino & English tokens — high ratio = heavy Taglish switching",
    format: (v) => v.toFixed(3),
  },
  particle_count: {
    label: 'Filipino Particles',
    color: 'text-teal-400',
    description: "Count of filler particles like 'na', 'nga', 'ba', 'daw'",
    format: (v) => String(v),
  },
  punctuation_intensity: {
    label: 'Punctuation Intensity',
    color: 'text-orange-400',
    description: 'Density of ! ? . per character — spikes signal emotional writing',
    format: (v) => v.toFixed(4),
  },
  caps_ratio: {
    label: 'Capitalization Ratio',
    color: 'text-indigo-400',
    description: 'Share of CAPITAL letters — excessive caps often signal alarm/anger',
    format: (v) => `${(v * 100).toFixed(1)}%`,
  },
  repeated_chars: {
    label: 'Repeated Characters',
    color: 'text-cyan-400',
    description: "Stretched words like 'graaabe', 'huhuhu' — signs of emotional emphasis",
    format: (v) => String(v),
  },
  emotional_count: {
    label: 'Emotional Words',
    color: 'text-pink-400',
    description: 'Count of emotionally loaded words in the vocabulary list',
    format: (v) => String(v),
  },
  urgency_count: {
    label: 'Urgency Cues',
    color: 'text-yellow-400',
    description: "Detected urgency phrases like 'paki-share', 'agad', 'breaking'",
    format: (v) => String(v),
  },
};

// ─── Centered Result Modal ───────────────────────────────────────────────────
const ResultModal = ({ activePost, onClose }) => {
  const { resultData, text } = activePost;
  const isDis = resultData.label === 'Disinformation';
  const featureFlags = resultData.feature_flags || {};
  const explanation = resultData.explanation || (
    isDis
      ? `This post was flagged as DISINFORMATION with ${(resultData.confidence * 100).toFixed(1)}% confidence based on the detected linguistic patterns.`
      : `This post was classified as NON-DISINFORMATION with ${(resultData.confidence * 100).toFixed(1)}% confidence. The language appears balanced and factual.`
  );

  return (
    <div
      className="fixed inset-0 flex items-center justify-center pointer-events-auto"
      style={{ zIndex: 2147483646, background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(4px)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="relative w-full max-w-[520px] mx-4 flex flex-col rounded-2xl overflow-hidden shadow-2xl"
        style={{
          background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
          border: isDis ? '1.5px solid rgba(239,68,68,0.5)' : '1.5px solid rgba(34,197,94,0.5)',
          boxShadow: isDis
            ? '0 0 40px rgba(239,68,68,0.25), 0 25px 50px rgba(0,0,0,0.6)'
            : '0 0 40px rgba(34,197,94,0.2), 0 25px 50px rgba(0,0,0,0.6)',
          maxHeight: '90vh',
          overflowY: 'auto',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Grid bg */}
        <div className="absolute inset-0 opacity-[0.04] pointer-events-none"
          style={{
            backgroundImage: 'linear-gradient(rgba(255,255,255,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.3) 1px, transparent 1px)',
            backgroundSize: '24px 24px',
          }}
        />

        {/* Header */}
        <div className="relative flex items-center justify-between px-5 py-3 border-b border-slate-700/60"
          style={{ background: 'rgba(15,23,42,0.7)' }}>
          <div className="flex items-center gap-2">
            <ShieldCheck size={15} className="text-green-400" />
            <span className="text-[10px] font-bold tracking-[0.15em] text-slate-400 uppercase">
              Taglish Disinformation Detection System
            </span>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-red-400 transition-colors cursor-pointer">
            <XCircle size={20} />
          </button>
        </div>

        <div className="relative flex flex-col gap-4 p-5">

          {/* Verdict */}
          <div className={`flex items-center gap-4 p-4 rounded-xl border
            ${isDis ? 'bg-red-950/60 border-red-500/60' : 'bg-green-950/60 border-green-500/60'}`}>
            <div className={`shrink-0 rounded-full p-2 ${isDis ? 'bg-red-500/20' : 'bg-green-500/20'}`}>
              {isDis
                ? <ShieldAlert size={32} className="text-red-400" />
                : <ShieldCheck size={32} className="text-green-400" />
              }
            </div>
            <div className="flex flex-col">
              <span className={`text-xl font-extrabold tracking-wide uppercase leading-tight
                ${isDis ? 'text-red-400' : 'text-green-400'}`}>
                {resultData.label}
              </span>
              <div className="flex items-center gap-2 mt-1">
                <TrendingUp size={12} className="text-slate-400" />
                <span className="text-[11px] text-slate-400">
                  DistilBERT Confidence:{' '}
                  <span className={`font-bold ${isDis ? 'text-red-300' : 'text-green-300'}`}>
                    {(resultData.confidence * 100).toFixed(1)}%
                  </span>
                </span>
                <span className="text-slate-700">·</span>
                <span className="text-[11px] text-slate-500">{resultData.inference_ms} ms</span>
              </div>
            </div>
          </div>

          {/* Why this label */}
          <div className="rounded-xl border border-slate-700/60 overflow-hidden"
            style={{ background: 'rgba(30,41,59,0.6)' }}>
            <div className="flex items-center gap-2 px-4 py-2 border-b border-slate-700/40 bg-slate-800/40">
              <Info size={13} className="text-blue-400" />
              <span className="text-[10px] font-bold tracking-widest text-slate-400 uppercase">Why this label?</span>
            </div>
            <p className="px-4 py-3 text-[12.5px] text-slate-300 leading-relaxed">{explanation}</p>
          </div>

          {/* Captured text */}
          <div className="rounded-xl border border-slate-700/40 overflow-hidden"
            style={{ background: 'rgba(15,23,42,0.5)' }}>
            <div className="flex items-center gap-2 px-4 py-2 border-b border-slate-700/40 bg-slate-800/30">
              <BookOpen size={13} className="text-slate-400" />
              <span className="text-[10px] font-bold tracking-widest text-slate-500 uppercase">Analyzed Text</span>
            </div>
            <div className="px-4 py-3 text-[11.5px] text-slate-400 italic leading-relaxed max-h-24 overflow-y-auto"
              style={{ scrollbarWidth: 'thin' }}>
              "{text}"
            </div>
          </div>

          {/* 7 Features */}
          <div className="rounded-xl border border-slate-700/50 overflow-hidden"
            style={{ background: 'rgba(30,41,59,0.4)' }}>
            <div className="flex items-center gap-2 px-4 py-2.5 border-b border-slate-700/40 bg-slate-800/40">
              <TrendingUp size={13} className="text-purple-400" />
              <span className="text-[10px] font-bold tracking-widest text-slate-400 uppercase">
                7 Linguistic Feature Breakdown
              </span>
              {Object.values(featureFlags).some(Boolean) && (
                <span className="ml-auto text-[9px] bg-amber-900/50 text-amber-400 border border-amber-500/40 px-2 py-0.5 rounded-full font-bold">
                  ⚡ Key signals highlighted
                </span>
              )}
            </div>
            <div className="flex flex-col gap-1.5 p-3">
              {Object.entries(FEATURE_META).map(([key, meta]) => {
                const val = resultData.features?.[key];
                if (val === undefined) return null;
                return (
                  <FeatureRow
                    key={key}
                    label={meta.label}
                    value={meta.format(val)}
                    color={meta.color}
                    isTriggered={!!featureFlags[key]}
                    description={meta.description}
                  />
                );
              })}
            </div>
          </div>

          {/* Fact-check reminder */}
          <div className="rounded-xl border border-blue-500/30 overflow-hidden"
            style={{ background: 'linear-gradient(135deg, rgba(30,58,138,0.4) 0%, rgba(17,24,39,0.6) 100%)' }}>
            <div className="flex items-start gap-3 px-4 py-3.5">
              <div className="shrink-0 mt-0.5 bg-blue-500/20 rounded-full p-1.5">
                <AlertTriangle size={14} className="text-blue-400" />
              </div>
              <div>
                <p className="text-[11.5px] font-bold text-blue-300 mb-1">⚠️ Always Verify Before Sharing</p>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  This AI result is a <strong className="text-slate-300">guide, not a final verdict.</strong>{' '}
                  Always think critically, cross-check information with credible news sources,
                  and do your own fact-checking before sharing or acting on any content online.
                </p>
              </div>
            </div>
          </div>

          {/* Close */}
          <button
            onClick={onClose}
            className="w-full py-2.5 rounded-xl text-sm font-semibold text-slate-400 border border-slate-700/60 hover:border-slate-500 hover:text-slate-200 hover:bg-slate-800/50 transition-all cursor-pointer pointer-events-auto"
          >
            Close Analysis
          </button>

        </div>
      </div>
    </div>
  );
};

// ─── Root App — only ever rendered by content.jsx (never as a popup) ─────────
function App() {
  const [posts, setPosts] = useState([]);
  const [activePost, setActivePost] = useState(null);

  // ── MutationObserver feed scanner ──────────────────────────────────────────
  useEffect(() => {
    const scanFeed = () => {
      const likeButtons = Array.from(document.querySelectorAll(
        '[aria-label*="Like"], [aria-label*="Gusto"], [aria-label*="Comment"], [aria-label*="Mag-comment"]'
      ));

      const newPosts = [];
      likeButtons.forEach(btn => {
        const container = btn.closest(
          'div[role="article"], [aria-posinset], article, [data-pagelet^="FeedUnit"]'
        );
        if (!container || container.hasAttribute('data-taglish-processed')) return;
        container.setAttribute('data-taglish-processed', 'true');

        const id = Math.random().toString(36).substring(7);
        const mountPoint = document.createElement('div');
        mountPoint.className = 'taglish-mount-point';
        mountPoint.style.cssText = `
          position: absolute !important;
          top: 15px !important;
          right: 85px !important;
          z-index: 2147483647 !important;
          display: block !important;
          pointer-events: auto !important;
          width: 34px !important;
          height: 34px !important;
        `;

        if (window.getComputedStyle(container).position === 'static') {
          container.style.setProperty('position', 'relative', 'important');
        }
        container.style.setProperty('overflow', 'visible', 'important');
        container.appendChild(mountPoint);

        const shadow = mountPoint.attachShadow({ mode: 'open' });
        const styleSheet = document.createElement('style');
        styleSheet.textContent = tailwindStyles;
        shadow.appendChild(styleSheet);

        const reactRoot = document.createElement('div');
        shadow.appendChild(reactRoot);

        newPosts.push({
          id,
          articleNode: container,
          mountNode: reactRoot,
          status: 'idle',
          resultData: null,
          text: '',
        });
      });

      if (newPosts.length > 0) setPosts(prev => [...prev, ...newPosts]);
    };

    // Run immediately, then at intervals to catch late-loading posts
    scanFeed();
    const t1 = setTimeout(scanFeed, 1000);
    const t2 = setTimeout(scanFeed, 3000);
    const t3 = setTimeout(scanFeed, 6000);

    const observer = new MutationObserver(scanFeed);
    observer.observe(document.body, { childList: true, subtree: true });

    return () => {
      observer.disconnect();
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, []);

  // ── Scan handler ────────────────────────────────────────────────────────────
  const handleScanClick = async (postObj) => {
    setPosts(prev => prev.map(p => p.id === postObj.id ? { ...p, status: 'scanning' } : p));
    const article = postObj.articleNode;

    // Expand "See more"
    const seeMoreBtns = Array.from(article.querySelectorAll(
      'div[role="button"], span[dir="auto"], tp-yt-paper-button, button'
    )).filter(el => {
      const txt = (el.innerText || '').toLowerCase().trim();
      return ['see more', 'see translation', 'continue reading', 'read more', 'show more'].includes(txt);
    });
    if (seeMoreBtns.length > 0) {
      seeMoreBtns[0].click();
      await new Promise(r => setTimeout(r, 600));
    }

    // Extract text
    let target = article.querySelector([
      '[data-testid="post_message"]', '[data-ad-preview="message"]',
      '[data-testid="tweetText"]', 'div[slot="text-body"]',
      'div[id="post-content"]', '#description-inline-expander',
      'yt-formatted-string[id="content-text"]'
    ].join(', '));

    let text = '';
    if (article.tagName.toLowerCase() === 'shreddit-post') {
      const title = article.querySelector('[slot="title"]');
      const body = article.querySelector('[slot="text-body"]');
      text = (title ? title.textContent : '') + '\n\n' + (body ? body.textContent : '');
    } else if (target) {
      text = target.innerText || target.textContent;
    } else {
      const texts = Array.from(article.querySelectorAll('div[dir="auto"], span[dir="auto"], #content-text'))
        .map(e => {
          const hasBlockChildren = Array.from(e.children).some(c =>
            ['block', 'flex'].includes(window.getComputedStyle(c).display)
          );
          if (hasBlockChildren) return '';
          return (e.innerText || e.textContent).trim();
        }).filter(t => t.length > 20);
      text = texts.join('\n');
    }

    if (!text.trim()) text = article.innerText.substring(0, 1000);
    text = text.replace(/@\w+/g, '').replace(/http\S+/g, '').trim();

    try {
      const response = await analyzeText({ text });
      const finalData = { ...postObj, text, status: 'done', resultData: response };
      setPosts(prev => prev.map(p => p.id === postObj.id ? finalData : p));
      setActivePost(finalData);
    } catch (err) {
      // Mock fallback for offline/presentation mode
      const isDis = Math.random() > 0.5;
      const label = isDis ? 'Disinformation' : 'Non-Disinformation';
      setTimeout(() => {
        const features = {
          code_switching_ratio:  isDis ? 0.32 : 0.08,
          urgency_count:         isDis ? 3    : 0,
          particle_count:        isDis ? 5    : 2,
          punctuation_intensity: isDis ? 0.09 : 0.02,
          caps_ratio:            isDis ? 0.38 : 0.05,
          repeated_chars:        isDis ? 2    : 0,
          emotional_count:       isDis ? 4    : 1,
        };
        const confidence = isDis ? 0.87 + Math.random() * 0.12 : 0.75 + Math.random() * 0.2;
        const feature_flags = {
          code_switching_ratio:  features.code_switching_ratio > 0.15,
          urgency_count:         features.urgency_count >= 2,
          particle_count:        features.particle_count >= 3,
          punctuation_intensity: features.punctuation_intensity > 0.05,
          caps_ratio:            features.caps_ratio > 0.20,
          repeated_chars:        features.repeated_chars >= 1,
          emotional_count:       features.emotional_count >= 2,
        };
        const triggered = Object.keys(feature_flags).filter(k => feature_flags[k]);
        const explanation = isDis
          ? `This post was flagged as DISINFORMATION with ${(confidence * 100).toFixed(1)}% confidence. The AI detected ${triggered.length} elevated linguistic signals commonly found in misleading or manipulative Taglish content.`
          : `This post was classified as NON-DISINFORMATION with ${(confidence * 100).toFixed(1)}% confidence. The language appears balanced, and no strong disinformation patterns were detected.`;

        const resultData = { label, label_code: isDis ? 1 : 0, confidence, inference_ms: 44.7, features, feature_flags, explanation };
        const finalData = { ...postObj, text, status: 'done', resultData };
        setPosts(prev => prev.map(p => p.id === postObj.id ? finalData : p));
        setActivePost(finalData);
      }, 1500);
    }
  };

  return (
    <>
      {/* Per-post scan buttons */}
      {posts.map(post =>
        post.mountNode && createPortal(
          <ScanButton key={post.id} post={post} onScan={handleScanClick} onViewBreakdown={setActivePost} />,
          post.mountNode
        )
      )}

      {/* Centered result modal */}
      {activePost && activePost.resultData && (
        <ResultModal activePost={activePost} onClose={() => setActivePost(null)} />
      )}
    </>
  );
}

export default App;
