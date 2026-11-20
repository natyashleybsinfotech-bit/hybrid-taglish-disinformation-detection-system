// Source lookup belongs to one displayed result. Never resurrect a cleared
// result or attach an older post's references to a newer prediction.
export function mergeRelatedSources(current, requestedResult, sources) {
  if (!current || current !== requestedResult) return current;
  const related = Array.isArray(sources?.related_sources) ? sources.related_sources : [];
  const assessed = (current.related_sources || []).filter(source => ['supports', 'contradicts'].includes(source.relationship));
  const retained = new Set(assessed.map(source => source.url));
  return { ...current, retrieval_status: sources?.retrieval_status || 'unavailable',
    related_sources: [...assessed, ...related.filter(source => !retained.has(source.url))] };
}

export function checkedMaterialLabel(value, extraction, language) {
  const key = String(value || '').toLowerCase();
  const tl = language === 'tl';
  if (extraction?.caption_fallback_used === true || key === 'video caption only') return tl ? 'Caption lang ng video' : 'Video caption only';
  if (extraction && typeof extraction === 'object') {
    const parts = [];
    if (extraction.caption_text?.trim()) parts.push(tl ? 'Caption ng post' : 'Post caption');
    if (extraction.transcript_text?.trim()) parts.push(tl ? 'Salitang narinig sa video' : 'Spoken audio');
    if (extraction.frame_ocr_text?.trim()) parts.push(tl ? 'Tekstong nasa mga video frame' : 'Text in video frames');
    if (extraction.ocr_text?.trim()) parts.push(tl ? 'Tekstong nakita sa image' : 'Text in the image');
    if (parts.length) return parts.join(' · ');
  }
  if (key.includes('video audio transcript') || key.includes('video-frame ocr')) return tl ? 'Salita at tekstong nasa video' : 'Spoken audio and video text';
  if (key.includes('image ocr')) return tl ? 'Tekstong nakita sa image' : 'Text in the image';
  if (key.includes('caption')) return tl ? 'Caption ng post' : 'Post caption';
  if (key.includes('selected')) return tl ? 'Piniling teksto' : 'Selected text';
  return value;
}

export function displayPostDate(context = {}, language = 'en') {
  const parsed = Date.parse(context.published_at || '');
  if (Number.isFinite(parsed)) {
    return new Intl.DateTimeFormat(language === 'tl' ? 'fil-PH' : 'en-PH',
      { dateStyle: 'medium', timeStyle: 'short' }).format(parsed);
  }
  return context.published_text || context.timing || (language === 'tl' ? 'Hindi available' : 'Not available');
}

export function displayPostRecency(context = {}, language = 'en', now = Date.now()) {
  const parsed = Date.parse(context.published_at || '');
  if (Number.isFinite(parsed) && parsed <= now) {
    const minutes = Math.floor((now - parsed) / 60000);
    const [value, unit] = minutes < 60 ? [Math.max(1, minutes), 'minute']
      : minutes < 2880 ? [Math.floor(minutes / 60), 'hour']
      : [Math.floor(minutes / 1440), 'day'];
    return new Intl.RelativeTimeFormat(language === 'tl' ? 'fil-PH' : 'en-PH',
      { numeric: 'auto' }).format(-value, unit);
  }
  const relative = String(context.published_text || '').trim().toLowerCase();
  const match = relative.match(/^(\d+)\s*(m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days|w|week|weeks|mo|month|months|y|year|years)\b/);
  if (match) {
    const unit = /^m(?!o)/.test(match[2]) ? 'minute' : /^h/.test(match[2]) ? 'hour'
      : /^d/.test(match[2]) ? 'day' : /^w/.test(match[2]) ? 'week'
      : /^mo/.test(match[2]) ? 'month' : 'year';
    return new Intl.RelativeTimeFormat(language === 'tl' ? 'fil-PH' : 'en-PH',
      { numeric: 'auto' }).format(-Number(match[1]), unit);
  }
  return context.recency && context.recency !== 'Could not determine'
    ? context.recency : (language === 'tl' ? 'Hindi matukoy' : 'Could not determine');
}

export function incompleteVideoNotice(extraction, language) {
  if (!['partial', 'failed'].includes(extraction?.frame_ocr_status)) return '';
  return language === 'tl'
    ? 'Hindi nabasa ang teksto sa ilang video frame. Kulang ang pagkuha ng on-screen text; ihambing ang nakuhang salita sa orihinal na video bago magpatuloy.'
    : 'Text could not be read from some video frames. On-screen text extraction is incomplete; compare the extracted speech with the original video before continuing.';
}

export function evidenceReaderNotice(result, language = 'en') {
  if (result?.decision_source === 'verified_evidence') return '';
  const status = result?.evidence_reader?.status;
  const tl = language === 'tl';
  if (status === 'rate_limited' || status === 'busy') return tl
    ? 'Hindi natapos ang paghahambing ng ebidensiya dahil abala o naabot ang limit ng serbisyo. Hindi pa beripikadong model prediction ang label na ito.'
    : 'Evidence comparison could not complete because the service is busy or its request limit was reached. This label is an unverified model prediction.';
  if (['unavailable','authentication_failed','invalid_configuration','not_configured','invalid_response','incomplete_response','input_too_long','source_limit_exceeded'].includes(status)) return tl
    ? 'Hindi natapos ang paghahambing ng ebidensiya. Hindi ito patunay na mali ang post; hindi pa beripikadong model prediction ang label na ito.'
    : 'Evidence comparison could not complete. This does not establish that the post is false; this label is an unverified model prediction.';
  if (status === 'no_readable_sources') return tl
    ? 'Walang nabasang buong artikulo para ikumpara. Hindi ito patunay na mali ang post; hindi pa beripikadong model prediction ang label na ito.'
    : 'No readable article was available for comparison. This does not establish that the post is false; this label is an unverified model prediction.';
  return '';
}
