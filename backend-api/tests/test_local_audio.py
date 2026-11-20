"""Local speech path keeps complete audio and separates bad speech from outage."""
import sys,unittest,tempfile
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'src')]
import media_processing as media

class LocalAudioTests(unittest.TestCase):
 def setUp(self):media.clear_video_extraction_cache();self.addCleanup(media.clear_video_extraction_cache)
 def test_full_audio_uses_one_local_function_before_frame_ocr(self):
  seen=[]
  def decode(args):Path(args[-1]).write_bytes(b'fixture')
  def speech(audio,**kwargs):
   self.assertEqual(len(audio),64000);seen.append('speech')
   return ([{'start_seconds':0,'end_seconds':4,'text':'Complete original speech.'}],'en','auto')
  def frames(paths):seen.append('frames');return [(p.name,640,360,[]) for p in paths],1
  with patch.object(media,'_run_ffmpeg',side_effect=decode),patch.object(media,'_read_pcm_wave',return_value=np.ones(64000)),patch.object(media,'_transcribe_local',side_effect=speech) as transcribe,patch.object(media,'_read_video_frames',side_effect=frames):
   result=media.process_video(b'complete-video')
  transcribe.assert_called_once();self.assertEqual(seen,['speech','frames'])
  self.assertEqual(result['transcript_text'],'Complete original speech.');self.assertEqual(result['transcript_source'],'local_whisper');self.assertEqual(result['timestamp_basis'],'decoder_segments')
 def test_bad_speech_and_missing_engine_remain_distinct(self):
  for error in [media.SpeechQualityError('unclear'),media.MediaProcessingError('Local engine unavailable')]:
   with patch.object(media,'_run_ffmpeg'),patch.object(media,'_read_pcm_wave',return_value=np.ones(16000)),patch.object(media,'_transcribe_local',side_effect=error),patch.object(media,'_read_video_frames') as frames:
    with self.assertRaises(type(error)):media.process_video(b'video'+str(type(error)).encode())
   frames.assert_not_called()
 def test_engine_is_forced_local_and_loading_cannot_download(self):
  import inspect,config
  self.assertEqual(config.SPEECH_PROVIDER,'local')
  source=inspect.getsource(media._get_whisper_model)
  self.assertIn('local_files_only=True',source)
  self.assertNotIn('gemini',source)

if __name__=='__main__':unittest.main()
