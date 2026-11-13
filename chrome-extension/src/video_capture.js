// Record only the selected element, at normal speed, from its beginning.
// A timer expiring or a changed/removed video is a failure, never a full clip.
export async function captureVideoElement(video) {
  if (!video || typeof video.captureStream !== 'function') throw new Error('This browser did not expose a capturable video stream. Use the video file upload instead.');
  const duration = video.duration;
  if (!Number.isFinite(duration) || duration <= 0) throw new Error('The video duration is not ready yet. Play it briefly, then try again.');
  if (duration > 180) throw new Error('The video exceeds the 3-minute limit. Choose a shorter clip.');
  const source = video.currentSrc || video.src;
  const previousRate = video.playbackRate;
  let stream, recorder, stopped;
  try {
    video.loop = false; video.autoplay = false; video.playbackRate = 1; video.pause();
    if (video.currentTime > .05) {
      await new Promise((resolve, reject) => {
        const cleanup = () => { clearTimeout(timer); video.removeEventListener('seeked', onSeeked); };
        const onSeeked = () => { cleanup(); resolve(); };
        const timer = setTimeout(() => { cleanup(); reject(new Error('The video could not be rewound for a complete audio capture.')); }, 5000);
        video.addEventListener('seeked', onSeeked, { once: true }); video.currentTime = 0;
      });
    }
    stream = video.captureStream();
    if (!stream.getAudioTracks().length) throw new Error('The selected video has no capturable audio track. No video prediction was made.');
    if (!stream.getVideoTracks().length) throw new Error('The selected video has no capturable video frames. Use the original video file.');
    recorder = new MediaRecorder(stream, { mimeType: 'video/webm;codecs=vp8,opus' });
    const chunks = [];
    recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
    stopped = new Promise((resolve, reject) => {
      recorder.onerror = () => reject(new Error('The browser could not capture this video.'));
      recorder.onstop = () => resolve(new Blob(chunks, { type: 'video/webm' }));
    });
    // Attach a handler immediately even when playback fails before awaiting it.
    stopped.catch(() => {});
    recorder.start(1000);
    try { await video.play(); } catch { throw new Error('The selected video could not play from the beginning for capture.'); }
    await new Promise((resolve, reject) => {
      let done = false, highest = video.currentTime;
      const finish = error => {
        if (done) return; done = true; clearInterval(poll); clearTimeout(limit);
        video.removeEventListener('ended', ended); error ? reject(error) : resolve();
      };
      const ended = () => highest >= duration - .5 || video.currentTime >= duration - .5
        ? finish() : finish(new Error('The selected video ended before its full audio was captured.'));
      const poll = setInterval(() => {
        if (!video.isConnected || (video.currentSrc || video.src) !== source) {
          finish(new Error('The selected video changed during capture. Check the original post again.')); return;
        }
        if (video.error) { finish(new Error('The selected video could not be played completely.')); return; }
        highest = Math.max(highest, video.currentTime);
        if (video.ended || video.currentTime >= duration - .10) { ended(); return; }
        if (video.playbackRate !== 1) video.playbackRate = 1;
        if (video.paused) video.play().catch(() => finish(new Error('Video playback stopped before capture completed.')));
      }, 100);
      const limit = setTimeout(() => finish(new Error('Video capture timed out before the full clip was recorded. No partial video was submitted.')), (duration + 10) * 1000);
      video.addEventListener('ended', ended, { once: true });
    });
    recorder.stop();
    const blob = await stopped;
    if (!blob.size) throw new Error('The captured video was empty.');
    return blob;
  } finally {
    if (recorder && recorder.state !== 'inactive') recorder.stop();
    if (stopped) await stopped.catch(() => {});
    stream?.getTracks().forEach(track => track.stop());
    video.pause(); video.playbackRate = previousRate;
  }
}
