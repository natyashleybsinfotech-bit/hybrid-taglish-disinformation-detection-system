import io,json,sys,unittest,wave
from pathlib import Path
from unittest.mock import patch
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'src')]
import gemini_audio as audio

def wav(seconds=21):
    out=io.BytesIO()
    with wave.open(out,'wb') as stream:
        stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(16000);stream.writeframes(b'\x01\x00'*(16000*seconds))
    return out.getvalue()

class AudioTests(unittest.TestCase):
    def test_all_audio_parts_are_required_and_unknown_or_duplicate_parts_fail(self):
        row={'chunk_id':'c1','text':'Original words.','unclear':False,'language':'tl'}
        self.assertEqual(audio.validate_parts({'chunks':[row]},['c1'])['c1']['text'],'Original words.')
        for rows in [[],[row,row],[{**row,'chunk_id':'invented'}]]:
            with self.assertRaises(ValueError):audio.validate_parts({'chunks':rows},['c1'])

    def test_unclear_parts_never_become_a_completed_transcript(self):
        with patch.object(audio,'transcribe_parts',return_value={'status':'assessed','chunks':{'c1':{'text':'[unclear]','unclear':True,'language':'tl'}}}):
            result=audio.transcribe_audio(wav(1),1)
        self.assertEqual(result['status'],'unclear');self.assertNotIn('transcript_text',result)

    def test_full_audio_is_split_once_with_server_owned_boundaries(self):
        def response(parts):
            self.assertEqual(len(parts),3)
            self.assertEqual([part['start'] for part in parts],[0,10,20])
            self.assertEqual([part['end'] for part in parts],[10,20,21])
            return {'status':'assessed','chunks':{p['chunk_id']:{'text':'Words '+p['chunk_id'],'unclear':False,'language':'tl'} for p in parts}}
        with patch.object(audio,'transcribe_parts',side_effect=response) as call:
            result=audio.transcribe_audio(wav(),21)
        call.assert_called_once();self.assertEqual(result['timestamp_basis'],'server_audio_chunks')
        self.assertEqual(result['segments'][-1]['end_seconds'],21)
        self.assertEqual(result['audio_parts'],3)

    def test_service_failure_or_invalid_audio_has_no_invented_transcript(self):
        with patch.object(audio,'transcribe_parts',return_value={'status':'rate_limited'}):
            result=audio.transcribe_audio(wav(1),1)
        self.assertEqual(result['status'],'rate_limited');self.assertNotIn('transcript_text',result)
        self.assertEqual(audio.transcribe_audio(b'bad-audio',1)['status'],'input_limit')
