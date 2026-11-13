export function statusTone(value) {
  const key = String(value ?? 'unknown').toLowerCase().replaceAll('_', ' ');
  // Negative states must be resolved before positive words: unavailable contains
  // available, and unverified/not configured must never look healthy.
  if (/\b(unavailable|inaccessible|error|failed|missing|rejected|down|offline|unreachable)\b|\bnot (available|connected|healthy)\b/.test(key)) return 'red';
  if (/\b(unverified|pending|warning|degraded|running|queued|revision|unknown)\b|\bnot (verified|configured|ready|assessed|tested)\b/.test(key)) return 'amber';
  if (/\b(available|configured|ready|approved|active|success|login|verified|connected|healthy|enabled)\b/.test(key)) return 'green';
  return 'secondary';
}
