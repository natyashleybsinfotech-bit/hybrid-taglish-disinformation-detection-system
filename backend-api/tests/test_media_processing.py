import os
import io
import tempfile
import wave
import sys
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import media_processing


class MediaProcessingTests(unittest.TestCase):


    def setUp(self):
        media_processing.clear_video_extraction_cache()
        self.speech_provider = patch.object(media_processing.config,"SPEECH_PROVIDER","local")
        self.speech_provider.start()
        self.addCleanup(self.speech_provider.stop)

    def test_video_cache_reuses_only_same_bytes_and_settings_with_detached_results(self):
        value={"extraction_status":"completed","transcript_text":"Original speech.","transcript_segments":[{"text":"Original speech."}],"processing_timings_ms":{"speech_transcription":100}}
        with patch.object(media_processing.config,"VIDEO_EXTRACTION_CACHE_ENABLED",True), patch.object(media_processing,"_process_video_uncached",return_value=value) as extract:
            first=media_processing.process_video(b"complete-video-a")
            first['transcript_segments'][0]['text']='Caller edit'
            second=media_processing.process_video(b"complete-video-a")
            self.assertTrue(second['extraction_cache_hit'])
            self.assertEqual(second['transcript_segments'][0]['text'],'Original speech.')
            self.assertIn('original_processing_timings_ms',second)
            self.assertEqual(extract.call_count,1)
            media_processing.process_video(b"complete-video-b")
            with patch.object(media_processing.config,'WHISPER_LANGUAGE_HINT','auto'):
                media_processing.process_video(b"complete-video-b")
            self.assertEqual(extract.call_count,3)

    def test_failed_and_partial_video_extractions_are_not_cached(self):
        with patch.object(media_processing.config,"VIDEO_EXTRACTION_CACHE_ENABLED",True), patch.object(media_processing,"_process_video_uncached",side_effect=media_processing.MediaProcessingError('unclear')) as extract:
            for _ in range(2):
                with self.assertRaises(media_processing.MediaProcessingError):media_processing.process_video(b'failed-video')
            self.assertEqual(extract.call_count,2)
        with patch.object(media_processing,"_process_video_uncached",return_value={'extraction_status':'partial'}) as extract:
            media_processing.process_video(b'partial-video');media_processing.process_video(b'partial-video')
            self.assertEqual(extract.call_count,2)

    def test_video_cache_expires_and_is_bounded(self):
        value={'extraction_status':'completed','transcript_text':'Complete speech.'}
        with patch.object(media_processing.config,'VIDEO_EXTRACTION_CACHE_ENABLED',True), patch.object(media_processing.config,'VIDEO_EXTRACTION_CACHE_TTL_SECONDS',10), patch.object(media_processing,'_process_video_uncached',side_effect=lambda *_args:dict(value)) as extract:
            with patch.object(media_processing.time,'monotonic',return_value=0):media_processing.process_video(b'first')
            with patch.object(media_processing.time,'monotonic',return_value=11):
                result=media_processing.process_video(b'first')
                self.assertFalse(result['extraction_cache_hit'])
                media_processing.process_video(b'second');media_processing.process_video(b'third')
            self.assertEqual(len(media_processing._video_cache),2)
            self.assertEqual(extract.call_count,4)

    def test_media_warmup_loads_configured_engines_without_transcribing(self):
        with patch.object(media_processing,'_get_whisper_model') as speech, patch.object(media_processing,'_get_ocr_reader') as ocr:
            result=media_processing.warm_media_engines()
        speech.assert_called_once();ocr.assert_called_once()
        speech.return_value.transcribe.assert_not_called()
        self.assertEqual(result['engines']['speech']['status'],'ready')
        self.assertEqual(result['engines']['image_text']['status'],'ready')

    def test_combine_text_normalizes_and_deduplicates(self):
        result = media_processing.combine_text(
            ["  Isang claim   dito.  ", "Duplicate"], ["duplicate", "Frame text"]
        )
        self.assertEqual(result, "Isang claim dito.\nDuplicate\nFrame text")

    def test_image_flow_uses_easyocr_output(self):
        from PIL import Image
        image_bytes = io.BytesIO()
        Image.new('RGB', (5, 5), 'white').save(image_bytes, format='PNG')
        fake_image = Mock()
        reader = Mock()
        reader.readtext.return_value = [(None, "Visible text", .95), (None, "visible   text", .91), (None, "Dagdag", .90)]
        with patch("media_processing._get_ocr_reader", return_value=reader), patch(
            "cv2.imdecode", return_value=fake_image
        ):
            result = media_processing.extract_image_text(image_bytes.getvalue())
        self.assertEqual(result["extraction_status"], "completed")
        self.assertEqual(result["ocr_text"], "Visible text\nDagdag")
        reader.readtext.assert_called_once_with(fake_image, detail=1, paragraph=False)

    def test_ocr_rejects_low_confidence_and_symbol_garbage(self):
        lines, rejected = media_processing._usable_ocr_lines([
            (None, "Clear public notice", .95), (None, "invented blurry words", .15),
            (None, "%%% ## #", .99), (None, "unscored"), (None, "invalid", float('nan')),
        ])
        self.assertEqual(lines, ["Clear public notice"])
        self.assertEqual(rejected, 4)

    def test_speech_diagnostics_preserve_actual_words_and_timestamps(self):
        segment = {"text": "  Basahin muna ang buong balita. ", "start": 1.5, "end": 4.0,
                   "avg_logprob": -.2, "no_speech_prob": .01, "compression_ratio": 1.2}
        result = media_processing._speech_segments({"segments": [segment], "text": "A conflicting unverified top-level string"})
        self.assertEqual(result, [{"start_seconds": 1.5, "end_seconds": 4.0, "text": "Basahin muna ang buong balita."}])

    def test_streaming_quality_failure_stops_later_chunks_and_still_fails_normal_gate(self):
        consumed=[];closed=[]
        def stream():
            try:
                for index,logprob in enumerate([-.2,-2.0,-.2]):
                    consumed.append(index)
                    yield SimpleNamespace(text='Complete spoken segment.',start=index*3,end=index*3+2,avg_logprob=logprob,no_speech_prob=.01,compression_ratio=1.2)
            finally:closed.append(True)
        model=Mock();model.transcribe.return_value=(stream(),SimpleNamespace(language='tl'))
        result=media_processing._FasterWhisperAdapter(model).transcribe(b'audio',logprob_threshold=-1.0)
        self.assertEqual(consumed,[0,1]);self.assertEqual(closed,[True])
        with self.assertRaises(media_processing.SpeechQualityError):media_processing._speech_segments(result)

    def test_optimized_whisper_adapter_preserves_original_words_and_diagnostics(self):
        model = Mock()
        segment = SimpleNamespace(text=' Cyber libel ang sinabi.', start=1.0, end=3.0,
                                  avg_logprob=-.2, no_speech_prob=.01, compression_ratio=1.2)
        model.transcribe.return_value = (iter([segment]), SimpleNamespace(language='tl'))
        result = media_processing._FasterWhisperAdapter(model).transcribe(
            b'audio', fp16=False, task='transcribe', language='tl',
            logprob_threshold=-1.0, temperature=0.0,
        )
        self.assertEqual(result['text'], 'Cyber libel ang sinabi.')
        self.assertEqual(result['segments'][0]['avg_logprob'], -.2)
        options = model.transcribe.call_args.kwargs
        self.assertEqual(options['task'], 'transcribe')
        self.assertEqual(options['language'], 'tl')
        self.assertEqual(options['log_prob_threshold'], -1.0)
        self.assertTrue(options['vad_filter'])
        self.assertEqual(options['vad_parameters'], {
            'threshold': .35, 'min_silence_duration_ms': 750, 'speech_pad_ms': 400,
        })

    def test_language_detection_uses_english_only_when_all_long_clip_samples_agree(self):
        import numpy as np
        model = Mock()
        adapter = media_processing._FasterWhisperAdapter(model)
        audio = np.zeros(16000 * 62, dtype=np.float32)
        with patch.object(media_processing.config, 'WHISPER_LANGUAGE_HINT', 'tl'), patch.object(media_processing.config, 'WHISPER_ENGINE', 'faster-whisper'):
            model.detect_language.side_effect = [('en', .99, []), ('en', .98, []), ('en', .99, [])]
            self.assertEqual(media_processing._transcription_language(adapter, audio),
                             (None, 'detected_english'))
            self.assertEqual(model.detect_language.call_count,3)
            model.detect_language.reset_mock()
            model.detect_language.side_effect = [('en', .99, []), ('tl', .96, []), ('en', .99, [])]
            self.assertEqual(media_processing._transcription_language(adapter, audio),
                             ('tl', 'configured'))
            self.assertEqual(model.detect_language.call_count,2)
            model.detect_language.reset_mock()
            model.detect_language.side_effect = [('en', .8, [])]
            self.assertEqual(media_processing._transcription_language(adapter, audio),('tl','configured'))
            self.assertEqual(model.detect_language.call_count,1)
            model.detect_language.reset_mock()
            self.assertEqual(media_processing._transcription_language(adapter, audio[:16000 * 30]),
                             ('tl', 'configured'))
            model.detect_language.assert_not_called()

    def test_uncertain_speech_is_not_silently_screened_as_complete(self):
        valid = {"text": "This is a complete spoken sentence.", "start": 0, "end": 3,
                 "avg_logprob": -.2, "no_speech_prob": .01, "compression_ratio": 1.2}
        for changes in ({"avg_logprob": -2}, {"no_speech_prob": .9}, {"compression_ratio": 3},
                        {"avg_logprob": float('nan')}, {"end": -1},
                        {"text": "thank you " * 12}):
            with self.subTest(changes=changes), self.assertRaisesRegex(media_processing.MediaProcessingError, "No prediction"):
                media_processing._speech_segments({"segments": [valid, valid | changes]})

    def test_top_level_speech_without_segment_diagnostics_is_not_accepted(self):
        with self.assertRaisesRegex(media_processing.MediaProcessingError, "Speech quality"):
            media_processing._speech_segments({"text": "Words without any acoustic quality information"})

    def test_missing_middle_speech_is_rejected(self):
        clean = {"avg_logprob": -.2, "no_speech_prob": .01, "compression_ratio": 1.2}
        with self.assertRaisesRegex(media_processing.MediaProcessingError, "middle section"):
            media_processing._speech_segments({"segments": [
                clean | {"start": 0, "end": 4, "text": "Unang bahagi ng balita."},
                clean | {"start": 15, "end": 19, "text": "Huling bahagi ng balita."},
            ]})


    def test_silent_video_skips_whisper_and_identifies_frame_text(self):
        import numpy as np
        def fake_decode(arguments):
            if '-ss' in arguments:
                from pathlib import Path
                Path(arguments[-1]).write_bytes(b'frame')
        reader = Mock()
        reader.readtext.return_value = [
            ([(150, 270), (450, 270), (450, 300), (150, 300)], 'Read the complete notice.', .95),
            ([(0, 335), (400, 335), (400, 350), (0, 350)], 'Unrelated ticker headline', .95),
        ]
        with tempfile.TemporaryDirectory() as folder, patch.object(media_processing.config, 'TEMP_MEDIA_DIR', __import__('pathlib').Path(folder)), patch.object(media_processing, '_run_ffmpeg', side_effect=fake_decode), patch.object(media_processing, '_read_pcm_wave', return_value=np.zeros(16000)), patch.object(media_processing, '_get_whisper_model') as whisper, patch('cv2.imread', return_value=np.zeros((360, 640, 3), dtype=np.uint8)), patch.object(media_processing, '_get_ocr_reader', return_value=reader):
            result = media_processing.process_video(b'video')
        whisper.assert_not_called()
        self.assertEqual(result['transcript_text'], '')
        self.assertEqual(result['transcript_status'], 'no_reliable_speech')
        self.assertEqual(result['frame_ocr_text'], 'Read the complete notice.')
        self.assertEqual(result['discarded_ocr_detections'], 1)
        self.assertEqual(result['frame_ocr_regions'][0]['sample_seconds'], 0.5)

    def test_video_uses_segment_text_and_samples_full_duration(self):
        import numpy as np
        from pathlib import Path
        calls = []
        def fake_decode(arguments):
            calls.append(arguments)
            if '-ss' in arguments:
                Path(arguments[-1]).write_bytes(b'frame')
        whisper = Mock()
        whisper.transcribe.return_value = {'language': 'tl', 'text': 'Do not use this inconsistent top-level text.', 'segments': [
            {'text': 'Basahin muna ang buong balita.', 'start': 0, 'end': 3, 'avg_logprob': -.2, 'no_speech_prob': .01, 'compression_ratio': 1.2}]}
        reader = Mock()
        reader.readtext.return_value = []
        with tempfile.TemporaryDirectory() as folder, patch.object(media_processing.config, 'TEMP_MEDIA_DIR', Path(folder)), patch.object(media_processing.config, 'VIDEO_MAX_FRAMES', 3), patch.object(media_processing, '_run_ffmpeg', side_effect=fake_decode), patch.object(media_processing, '_read_pcm_wave', return_value=np.full(16000 * 90, .1)), patch.object(media_processing, '_get_whisper_model', return_value=whisper), patch('cv2.imread', return_value=np.zeros((360, 640, 3), dtype=np.uint8)), patch.object(media_processing, '_get_ocr_reader', return_value=reader):
            result = media_processing.process_video(b'video')
        self.assertEqual(result['transcript_text'], 'Basahin muna ang buong balita.')
        self.assertNotIn('inconsistent', result['analyzed_text'])
        self.assertEqual(whisper.transcribe.call_args.kwargs['task'], 'transcribe')
        self.assertEqual(whisper.transcribe.call_args.kwargs['language'], 'tl')
        self.assertEqual(whisper.transcribe.call_args.kwargs['condition_on_previous_text'],
                         media_processing.config.WHISPER_ENGINE == 'faster-whisper')
        self.assertEqual(whisper.transcribe.call_args.kwargs['temperature'], 0.0)
        self.assertEqual([float(call[call.index('-ss') + 1]) for call in calls[1:]], [15.0, 45.0, 75.0])
        self.assertNotIn('-vf', calls[1])
        self.assertEqual(result['frame_ocr_status'], 'no_readable_text')
        self.assertEqual(result['failed_ocr_frames'], 0)

    def test_frame_reader_failure_is_not_reported_as_complete_video_extraction(self):
        import numpy as np
        from pathlib import Path
        def fake_decode(arguments):
            if '-ss' in arguments:
                Path(arguments[-1]).write_bytes(b'frame')
        whisper = Mock()
        whisper.transcribe.return_value = {'language': 'tl', 'segments': [
            {'text': 'Basahin ang buong balita.', 'start': 0, 'end': 3,
             'avg_logprob': -.2, 'no_speech_prob': .01, 'compression_ratio': 1.2}]}
        reader = Mock()
        reader.readtext.side_effect = RuntimeError('OCR engine unavailable')
        with tempfile.TemporaryDirectory() as folder, patch.object(media_processing.config, 'TEMP_MEDIA_DIR', Path(folder)), patch.object(media_processing, '_run_ffmpeg', side_effect=fake_decode), patch.object(media_processing, '_read_pcm_wave', return_value=np.full(16000 * 4, .1)), patch.object(media_processing, '_get_whisper_model', return_value=whisper), patch('cv2.imread', return_value=np.zeros((360, 640, 3), dtype=np.uint8)), patch.object(media_processing, '_get_ocr_reader', return_value=reader):
            result = media_processing.process_video(b'video')
        self.assertEqual(result['extraction_status'], 'partial')
        self.assertEqual(result['frame_ocr_status'], 'failed')
        self.assertGreater(result['failed_ocr_frames'], 0)
        self.assertEqual(result['transcript_text'], 'Basahin ang buong balita.')
        self.assertEqual(result['frame_ocr_text'], '')
        self.assertIn('incomplete', result['quality_notice'])

    def test_different_language_frame_text_returns_both_originals_for_review(self):
        import numpy as np
        from pathlib import Path

        def fake_decode(arguments):
            if '-ss' in arguments:
                Path(arguments[-1]).write_bytes(b'frame')

        speech = 'Pag-aaralan ang reklamo kapag natanggap na ang kopya.'
        quote = 'We will review the matter and comment accordingly upon receipt.'
        whisper = Mock()
        whisper.transcribe.return_value = {'language': 'tl', 'segments': [
            {'text': speech, 'start': 0, 'end': 3, 'avg_logprob': -.2,
             'no_speech_prob': .01, 'compression_ratio': 1.2}]}
        reader = Mock()
        reader.readtext.return_value = [
            ([(150, 180), (500, 180), (500, 230), (150, 230)], quote, .95)]
        with tempfile.TemporaryDirectory() as folder, patch.object(media_processing.config, 'TEMP_MEDIA_DIR', Path(folder)), patch.object(media_processing, '_run_ffmpeg', side_effect=fake_decode), patch.object(media_processing, '_read_pcm_wave', return_value=np.full(16000 * 4, .1)), patch.object(media_processing, '_get_whisper_model', return_value=whisper), patch('cv2.imread', return_value=np.zeros((360, 640, 3), dtype=np.uint8)), patch.object(media_processing, '_get_ocr_reader', return_value=reader):
            result = media_processing.process_video(b'video')
        self.assertEqual(result['transcript_text'], speech)
        self.assertEqual(result['frame_ocr_text'], quote)
        self.assertEqual(result['speech_frame_agreement'], 'review_required')
        self.assertFalse(result['frame_ocr_included'])
        self.assertEqual(result['analyzed_text'], speech)
        self.assertIn('before confirming', result['quality_notice'])

    def test_english_retry_recovers_only_after_failed_filipino_hint(self):
        import numpy as np
        from pathlib import Path
        def fake_decode(arguments):
            if '-ss' in arguments:
                Path(arguments[-1]).write_bytes(b'frame')
        bad = {'text': 'Powered by ' * 30, 'start': 0, 'end': 3,
               'avg_logprob': -.1, 'no_speech_prob': .01, 'compression_ratio': 20}
        clean = {'text': 'Read the complete report before sharing.', 'start': 0, 'end': 3,
                 'avg_logprob': -.2, 'no_speech_prob': .01, 'compression_ratio': 1.2}
        whisper = Mock()
        whisper.transcribe.side_effect = [
            {'language': 'tl', 'segments': [bad]},
            {'language': 'en', 'segments': [clean]},
        ]
        with tempfile.TemporaryDirectory() as folder, patch.object(media_processing.config, 'TEMP_MEDIA_DIR', Path(folder)), patch.object(media_processing.config, 'WHISPER_ENGINE', 'faster-whisper'), patch.object(media_processing.config, 'WHISPER_LANGUAGE_HINT', 'tl'), patch.object(media_processing, '_run_ffmpeg', side_effect=fake_decode), patch.object(media_processing, '_read_pcm_wave', return_value=np.full(16000 * 4, .1)), patch.object(media_processing, '_get_whisper_model', return_value=whisper), patch('cv2.imread', return_value=np.zeros((360, 640, 3), dtype=np.uint8)), patch.object(media_processing, '_get_ocr_reader') as reader:
            reader.return_value.readtext.return_value = []
            result = media_processing.process_video(b'video')
        self.assertEqual(result['transcript_text'], 'Read the complete report before sharing.')
        self.assertEqual(result['speech_language'], 'en')
        self.assertEqual(result['speech_language_mode'], 'auto_retry_after_quality_failure')
        self.assertEqual([call.kwargs['language'] for call in whisper.transcribe.call_args_list], ['tl', None])

    def test_audible_video_never_substitutes_frame_ocr_for_missing_speech(self):
        import numpy as np
        from pathlib import Path
        whisper = Mock()
        whisper.transcribe.return_value = {'language': 'tl', 'segments': [], 'text': ''}
        with tempfile.TemporaryDirectory() as folder, patch.object(media_processing.config, 'TEMP_MEDIA_DIR', Path(folder)), patch.object(media_processing, '_run_ffmpeg'), patch.object(media_processing, '_read_pcm_wave', return_value=np.full(16000, .1)), patch.object(media_processing, '_get_whisper_model', return_value=whisper):
            with self.assertRaisesRegex(media_processing.MediaProcessingError, 'No reliable speech'):
                media_processing.process_video(b'video')

    def test_unrelated_detected_language_is_rejected_before_classification(self):
        import numpy as np
        from pathlib import Path
        whisper = Mock()
        whisper.transcribe.return_value = {'language': 'ja', 'segments': [
            {'text': 'Apparent words from the wrong language.', 'start': 0, 'end': 2,
             'avg_logprob': -.1, 'no_speech_prob': .01, 'compression_ratio': 1.1}]}
        with tempfile.TemporaryDirectory() as folder, patch.object(media_processing.config, 'TEMP_MEDIA_DIR', Path(folder)), patch.object(media_processing, '_run_ffmpeg'), patch.object(media_processing, '_read_pcm_wave', return_value=np.full(16000, .1)), patch.object(media_processing, '_get_whisper_model', return_value=whisper):
            with self.assertRaisesRegex(media_processing.MediaProcessingError, 'language could not be identified'):
                media_processing.process_video(b'video')

    def test_news_frame_ocr_keeps_lower_third_and_rejects_ticker_logo_clock(self):
        box = lambda x, y: [(x - 40, y - 6), (x + 40, y - 6), (x + 40, y + 6), (x - 40, y + 6)]
        regions, rejected = media_processing._story_frame_detections([
            (box(300, 290), 'REP: PAOLO DUTERTE, INIREKLAMO SINA MATIBAG', .94),
            (box(400, 336), 'Unrelated weather and birthday ticker', .98),
            (box(560, 40), 'GMA NEWS', .99),
            (box(320, 260), 'GMA NETWORK', .99),
            (box(60, 336), '07:29 PM', .99),
            (box(320, 170), 'THANKS FOR VATCHING!', .95),
        ], 640, 360, 23)
        self.assertEqual([item['text'] for item in regions], ['REP: PAOLO DUTERTE, INIREKLAMO SINA MATIBAG'])
        self.assertEqual(regions[0]['sample_seconds'], 23)
        self.assertEqual(rejected, 5)

    def test_spoken_bottom_subtitle_is_kept_but_unrelated_ticker_is_excluded(self):
        def box(x, y, half_width):
            return [(x - half_width, y - 7), (x + half_width, y - 7),
                    (x + half_width, y + 7), (x - half_width, y + 7)]
        regions, rejected = media_processing._story_frame_detections([
            (box(320, 336, 190), 'An intelligent assistant that uses the connections', .94),
            (box(320, 344, 270), 'Weather tomorrow and unrelated birthday updates', .98),
            (box(60, 336, 45), '07:29 PM', .99),
        ], 640, 360, 10, ['An intelligent assistant that uses all the connections.'])
        self.assertEqual([item['text'] for item in regions],
                         ['An intelligent assistant that uses the connections'])
        self.assertEqual(regions[0]['region_type'], 'subtitle')
        self.assertEqual(regions[0]['sample_seconds'], 10)
        self.assertEqual(rejected, 2)

    def test_speech_frame_disagreement_is_not_classified_as_one_story(self):
        self.assertFalse(media_processing._speech_frame_consistent(
            ['Status conference at trial chamber ang tinalakay.'],
            ['HINDI DADALO SA KASO NIYANG AGAINST HUMANITY'],
        ))
        self.assertTrue(media_processing._speech_frame_consistent(
            ['Naghain ng reklamong libel at cyberlibel si Paolo Duterte. Inireklamo rin si Matibag.'],
            ['REKLAMONG LIBEL AT CYBERLIBEL', 'PAOLO DUTERTE, INIREKLAMO SI MATIBAG'],
        ))
        self.assertFalse(media_processing._speech_frame_consistent(
            ['Naghain ng reklamong libel at cyber libel si Paulo Duterte laban kay Matibag.'],
            ['REKLAMONG LIBEL AI CYBERLIBEL',
             'REP: PAOLO DUTERTE, INIREKLAMO SINA MATIBAG,',
             'GRACIOSO AT ILANG PERSONALIDAD NG GMA'],
        ))
        self.assertTrue(media_processing._speech_frame_consistent(
            ['Dalawa ang patay matapos ang dump truck na bumangga sa rider ng habal-habal. Sugatan ang mga sakay.'],
            ['NABANGGA', 'TRUCK; RIDER', 'NA SAKAY NG DUMP TRUCK, SUGATAN'],
        ))

    def test_headline_titles_and_compound_spacing_do_not_cause_false_topic_mismatch(self):
        self.assertTrue(media_processing._speech_frame_consistent(
            ['Nagsampa ng reklamong cyber libel ang alkalde laban kay Aquino at Ramos. Kasama sa kaso ang dalawang opisyal.'],
            ['REKLAMONG CYBERLIBEL', 'REP: ALKALDE, INIREKLAMO SINA AQUINO, RAMOS AT DALAWANG OPISYAL'],
        ))
        self.assertFalse(media_processing._speech_frame_consistent(
            ['Nagsampa ng reklamong cyber libel ang alkalde laban kay Cruz sa Cebu.'],
            ['REKLAMONG CYBERLIBEL', 'REP: ALKALDE, INIREKLAMO SINA AQUINO, RAMOS AT DALAWANG OPISYAL'],
        ))

    def test_unreadable_image_has_clear_failure(self):
        with patch("cv2.imdecode", return_value=None):
            with self.assertRaisesRegex(media_processing.MediaProcessingError, "unreadable"):
                media_processing.extract_image_text(b"not-an-image")

    def test_service_health_reports_required_services(self):
        health = media_processing.service_health()
        self.assertEqual(set(health), {"easyocr", "whisper", "ffmpeg", "whisper_engine", "whisper_model", "whisper_language_hint", "whisper_vad_filter", "whisper_previous_text_context", "speech_engine_loaded", "ocr_engine_loaded", "video_extraction_cache_enabled", "speech_provider", "remote_speech_configured"})
        self.assertEqual(health['whisper_vad_filter'], media_processing.config.WHISPER_ENGINE == 'faster-whisper')

    def test_oversized_image_is_rejected_before_ocr(self):
        preview = Mock(width=5000, height=5000)
        preview.__enter__ = Mock(return_value=preview)
        preview.__exit__ = Mock(return_value=False)
        with patch('PIL.Image.open', return_value=preview), patch('media_processing._get_ocr_reader') as reader:
            with self.assertRaisesRegex(media_processing.MediaProcessingError, '20-megapixel'):
                media_processing.extract_image_text(b'fixture')
            reader.assert_not_called()

    def test_overlong_audio_is_rejected_without_partial_transcript(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'audio.wav')
            with wave.open(path, 'wb') as stream:
                stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(1); stream.writeframes(b'\0\0' * 181)
            with self.assertRaisesRegex(media_processing.MediaProcessingError, '180-second'):
                media_processing._read_pcm_wave(path)

    def test_exactly_three_minutes_of_audio_is_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'audio.wav')
            with wave.open(path, 'wb') as stream:
                stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(1); stream.writeframes(b'\0\0' * 180)
            self.assertEqual(len(media_processing._read_pcm_wave(path)), 180)

    def test_small_codec_padding_on_three_minute_clip_is_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'audio.wav')
            with wave.open(path, 'wb') as stream:
                stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(10); stream.writeframes(b'\0\0' * 1801)
            self.assertEqual(len(media_processing._read_pcm_wave(path)), 1801)


if __name__ == "__main__":
    unittest.main()
