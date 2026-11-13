const normalize = (value) => typeof value === 'string' ? value.replace(/\s+/g, ' ').trim() : '';

function mediaIdentity(value) {
  if (typeof value !== 'string' || !value) return '';
  try {
    const url = new URL(value);
    return `${url.origin}${url.pathname}`;
  } catch {
    return normalize(value);
  }
}

export function postResultCacheKey(snapshot, mediaChoice) {
  const media = mediaChoice === 'image'
    ? [...new Set((snapshot?.media?.image_urls || []).map(mediaIdentity).filter(Boolean))].sort()
    : mediaChoice === 'video' ? mediaIdentity(snapshot?.media?.video_url) : '';
  return JSON.stringify({
    pageUrl: snapshot?.pageUrl || null,
    pageTitle: snapshot?.pageTitle || null,
    text: normalize(snapshot?.text),
    author: normalize(snapshot?.context?.author),
    postUrl: snapshot?.context?.original_post_url || null,
    mediaChoice,
    media,
  });
}

export function resolveMediaChoice(choice, media) {
  const hasImages = Array.isArray(media?.image_urls) && media.image_urls.length > 0;
  if (choice === 'video') return media?.has_video ? 'video' : 'unavailable';
  if (choice === 'image') return hasImages ? 'image' : 'unavailable';
  if (choice === 'text') return 'text';
  if (choice === 'auto' && (media?.has_video || hasImages)) return 'choose';
  return choice === 'auto' ? 'text' : 'unavailable';
}

export function captionForScreening(text, isComplete, mode) {
  return mode === 'text' || isComplete ? text : '';
}

export function matchesVideoPreview(preview, { text, pageUrl, pageTitle }) {
  if (!preview || preview.review_required !== true || typeof preview.review_token !== 'string'
      || !preview.review_token || (preview.page_url || null) !== (pageUrl || null)
      || (preview.page_title || null) !== (pageTitle || null)
      || normalize(preview.post_text) !== normalize(text)) return false;
  const extraction = preview.extraction;
  if (!extraction || typeof extraction !== 'object') return false;
  return Boolean(normalize(extraction.transcript_text)
    || (extraction.frame_ocr_included !== false && normalize(extraction.frame_ocr_text)));
}

export function isValidScreeningResult(result) {
  if (!result || typeof result !== 'object') return false;
  const labels = { Misleading: 'Potentially Misleading', 'Non-Misleading': 'No Misleading Information Detected' };
  const label = labels[result.internal_label];
  return Boolean(label) && result.public_label === label
    && (!Object.hasOwn(result, 'final_label') || result.final_label === label)
    && (result.screening_mode === 'evidence_only'
      ? result.model_score === null
      : typeof result.model_score === 'number' && Number.isFinite(result.model_score)
        && result.model_score >= 0 && result.model_score <= 1)
    && Boolean(normalize(result.analyzed_text));
}

export function requireScreeningResult(result) {
  if (!isValidScreeningResult(result)) throw new Error('The service returned an incomplete or inconsistent result. No prediction was displayed. Please retry.');
  return result;
}

// Verify the returned material against the exact caption and selected media.
export function matchesSubmittedPost(result, { text, mediaChoice, pageUrl, pageTitle }) {
  if (!isValidScreeningResult(result)) return false;
  if ((result.page_url || null) !== (pageUrl || null) || (result.page_title || null) !== (pageTitle || null)) return false;

  const caption = normalize(text);
  const analyzed = normalize(result.analyzed_text);
  if (!analyzed) return false;

  if (mediaChoice === 'image') {
    const extractedCaption = normalize(result.extraction?.caption_text);
    const ocr = normalize(result.extraction?.ocr_text);
    return result.input_type === 'image' && Boolean(ocr) && extractedCaption === caption && analyzed === normalize(`${caption} ${ocr}`);
  }

  if (mediaChoice === 'video') {
    const extractedCaption = normalize(result.extraction?.caption_text);
    const seen = new Set();
    const mediaParts = [result.extraction?.transcript_text,
      result.extraction?.frame_ocr_included === false ? '' : result.extraction?.frame_ocr_text]
      .flatMap(value => typeof value === 'string' ? value.split('\n') : [])
      .map(normalize)
      .filter(value => { const key = value.toLocaleLowerCase(); if (!value || seen.has(key)) return false; seen.add(key); return true; });
    return result.input_type === 'video' && mediaParts.length > 0 && extractedCaption === caption
      && analyzed === normalize([caption, ...mediaParts].filter(Boolean).join(' '));
  }

  return result.input_type === 'text' && analyzed === caption;
}
