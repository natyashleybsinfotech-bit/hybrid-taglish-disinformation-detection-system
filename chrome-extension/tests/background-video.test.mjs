import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

const source = readFileSync(new URL('../src/background.js', import.meta.url), 'utf8')
  .replaceAll('import.meta.env', '({})');

test('selected caption sends only the exact caption request and never downloads the video', async () => {
  let receive;
  const chrome = {runtime:{onInstalled:{addListener(){}},onConnect:{addListener(){}},
    onMessage:{addListener(listener){receive=listener;}}},storage:{local:{get(){},set(){}}}};
  const requests=[];
  runInNewContext(source,{chrome,Blob,FormData,URL,Uint8Array,AbortController,setTimeout,clearTimeout,
    fetch:async (url,options)=>{
      requests.push(url);
      assert.equal(url,'http://127.0.0.1:8000/analyze/video-caption');
      const body=JSON.parse(options.body);
      assert.equal(body.text,'Exact complete caption.');assert.equal(body.context.caption_complete,true);
      assert.equal(body.retrieve_sources,false);
      return new Response(JSON.stringify({input_type:'video',extraction_status:'caption_only',analyzed_text:body.text}));
    }});
  const result=await new Promise(resolve=>receive({type:'SURIPH_ANALYZE_VIDEO_CAPTION',payload:{
    text:'Exact complete caption.',context:{caption_complete:true},retrieve_sources:false,
  }},{},resolve));
  assert.equal(result.ok,true);assert.equal(result.result.extraction_status,'caption_only');assert.equal(requests.length,1);
});

test('caption endpoint failures return an error without a substitute prediction', async () => {
  let receive;
  const chrome={runtime:{onInstalled:{addListener(){}},onConnect:{addListener(){}},
    onMessage:{addListener(listener){receive=listener;}}},storage:{local:{get(){},set(){}}}};
  runInNewContext(source,{chrome,Blob,FormData,URL,Uint8Array,AbortController,setTimeout,clearTimeout,
    fetch:async()=>new Response(JSON.stringify({detail:'Screening unavailable'}),{status:503})});
  const result=await new Promise(resolve=>receive({type:'SURIPH_ANALYZE_VIDEO_CAPTION',payload:{text:'Complete caption.'}},{},resolve));
  assert.equal(result.ok,false);assert.equal(result.result,undefined);assert.match(result.error,/unavailable/);
});

function startVideoRequest(videoUrl, fetchImpl) {
  let onConnect;
  const chrome = {
    runtime: {
      onInstalled: { addListener() {} },
      onConnect: { addListener(listener) { onConnect = listener; } },
      onMessage: { addListener() {} },
    },
    storage: { local: { get() {}, set() {} } },
  };
  runInNewContext(source, { chrome, fetch: fetchImpl, Blob, FormData, URL,
    Uint8Array, AbortController, setTimeout, clearTimeout, atob });
  let onMessage;
  let resolveResult;
  const result = new Promise(resolve => { resolveResult = resolve; });
  onConnect({
    name: 'SURIPH_VIDEO_ANALYSIS',
    onDisconnect: { addListener() {} },
    onMessage: { addListener(listener) { onMessage = listener; } },
    postMessage(value) { if (value.type !== 'VIDEO_PROGRESS') resolveResult(value); },
  });
  onMessage({ type: 'ANALYZE_VIDEO', videoUrl,
    payload: { text: 'Exact selected caption', page_url: 'https://www.facebook.com/reel/123', retrieve_sources: true } });
  return result;
}

test('background direct video fetch uploads the selected media and caption without recording playback', async () => {
  const requested = [];
  const result = await startVideoRequest('https://cdn.fbcdn.net/selected.mp4', async (url, options) => {
    requested.push({ url, options });
    if (url.startsWith('https://')) return new Response(new Blob(['video bytes'], { type: 'video/mp4' }));
    const form = options.body;
    assert.equal(form.get('post_text'), 'Exact selected caption');
    assert.equal(form.get('page_url'), 'https://www.facebook.com/reel/123');
    assert.equal(form.get('retrieve_sources'), 'true');
    assert.equal(form.get('file').type, 'video/mp4');
    return new Response(JSON.stringify({ review_required: true, extraction: { transcript_text: 'sample' } }),
      { status: 200, headers: { 'Content-Type': 'application/json' } });
  });
  assert.equal(result.ok, true);
  assert.equal(result.result.review_required, true);
  assert.deepEqual(requested.map(item => item.url), [
    'https://cdn.fbcdn.net/selected.mp4', 'http://127.0.0.1:8000/analyze/video',
  ]);
  assert.equal(requested[0].options.credentials, 'include');
});

test('unavailable direct video URL explicitly permits complete capture fallback', async () => {
  const requested = [];
  const result = await startVideoRequest('https://cdn.fbcdn.net/expired.mp4', async url => {
    requested.push(url);
    throw new TypeError('Expired media URL');
  });
  assert.equal(result.ok, false);
  assert.equal(result.fallback_to_capture, true);
  assert.deepEqual(requested, ['https://cdn.fbcdn.net/expired.mp4']);
});

test('partial video response falls back instead of transcribing an incomplete clip', async () => {
  const requested = [];
  const result = await startVideoRequest('https://cdn.fbcdn.net/partial.mp4', async url => {
    requested.push(url);
    return new Response(new Blob(['partial'], { type: 'video/mp4' }), { status: 206 });
  });
  assert.equal(result.ok, false);
  assert.equal(result.fallback_to_capture, true);
  assert.deepEqual(requested, ['https://cdn.fbcdn.net/partial.mp4']);
});

test('backend extraction failure after a successful download does not repeat video capture', async () => {
  const requested = [];
  const result = await startVideoRequest('https://cdn.fbcdn.net/selected.mp4', async url => {
    requested.push(url);
    if (url.startsWith('https://')) return new Response(new Blob(['video bytes'], { type: 'video/mp4' }));
    return new Response(JSON.stringify({ detail: 'Speech quality is insufficient.' }),
      { status: 422, headers: { 'Content-Type': 'application/json' } });
  });
  assert.equal(result.ok, false);
  assert.equal(result.fallback_to_capture, false);
  assert.deepEqual(requested, [
    'https://cdn.fbcdn.net/selected.mp4', 'http://127.0.0.1:8000/analyze/video',
  ]);
});

test('a downloaded Facebook video without decodable audio permits playback capture', async () => {
  const requested = [];
  const result = await startVideoRequest('https://cdn.fbcdn.net/video-only.mp4', async url => {
    requested.push(url);
    if (url.startsWith('https://')) return new Response(new Blob(['video bytes'], { type: 'video/mp4' }));
    return new Response(JSON.stringify({ detail: 'FFmpeg could not process the submitted video.' }),
      { status: 422, headers: { 'Content-Type': 'application/json' } });
  });
  assert.equal(result.ok, false);
  assert.equal(result.fallback_to_capture, true);
  assert.deepEqual(requested, [
    'https://cdn.fbcdn.net/video-only.mp4', 'http://127.0.0.1:8000/analyze/video',
  ]);
});

test('one complete HTTP range does not require real-time recording', async () => {
  const result = await startVideoRequest('https://cdn.fbcdn.net/whole.mp4', async (url, options) => {
    if (url.startsWith('https://')) return new Response(new Blob(['whole video'], { type: 'video/mp4' }), {
      status: 206, headers: { 'Content-Range': 'bytes 0-10/11' },
    });
    assert.equal(await options.body.get('file').text(), 'whole video');
    return new Response(JSON.stringify({ review_required: true }));
  });
  assert.equal(result.ok, true);
});

test('contiguous validated video ranges are assembled before transcription', async () => {
  const requests = [];
  const result = await startVideoRequest('https://cdn.fbcdn.net/ranged.mp4', async (url, options) => {
    requests.push({ url, options });
    if (url.startsWith('https://')) {
      if (requests.length === 1) return new Response(new Blob(['first '], { type: 'video/mp4' }), {
        status: 206, headers: { 'Content-Range': 'bytes 0-5/11', ETag: '"stable"' },
      });
      assert.equal(options.headers.Range, 'bytes=6-10');
      assert.equal(options.headers['If-Range'], '"stable"');
      return new Response(new Blob(['video'], { type: 'video/mp4' }), {
        status: 206, headers: { 'Content-Range': 'bytes 6-10/11', ETag: '"stable"' },
      });
    }
    assert.equal(await options.body.get('file').text(), 'first video');
    return new Response(JSON.stringify({ review_required: true }));
  });
  assert.equal(result.ok, true); assert.equal(requests.length, 3);
});

test('changed validators or gapped ranges never reach the backend', async () => {
  for (const headers of [
    { 'Content-Range': 'bytes 6-10/11', ETag: '"different"' },
    { 'Content-Range': 'bytes 7-10/11', ETag: '"stable"' },
  ]) {
    let requests = 0;
    const result = await startVideoRequest('https://cdn.fbcdn.net/changed.mp4', async url => {
      assert.ok(url.startsWith('https://')); requests++;
      return requests === 1
        ? new Response(new Blob(['first ']), { status: 206, headers: { 'Content-Range': 'bytes 0-5/11', ETag: '"stable"' } })
        : new Response(new Blob(['video']), { status: 206, headers });
    });
    assert.equal(result.ok, false); assert.equal(result.fallback_to_capture, true);
  }
});

test('oversized declared videos are rejected without downloading or capturing', async () => {
  const result = await startVideoRequest('https://cdn.fbcdn.net/large.mp4', async url => {
    assert.ok(url.startsWith('https://'));
    return new Response(new Blob(['short']), { headers: { 'Content-Length': String(51 * 1024 * 1024) } });
  });
  assert.equal(result.ok, false); assert.equal(result.fallback_to_capture, false);
  assert.match(result.error, /50 MiB/);
});
