"""Small real synthetic OCR/video smoke checks; not a media accuracy study."""
import json
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend-api'),str(ROOT/'backend-api/src')]
from PIL import Image, ImageDraw, ImageFont
from media_processing import extract_image_text, process_video, ffmpeg_executable
folder=ROOT/'tmp/media-check';folder.mkdir(parents=True,exist_ok=True)
image=Image.new('RGB',(1000,220),'white');draw=ImageDraw.Draw(image)
draw.text((35,60),'Read the full article before sharing.',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',42),fill='black')
image.save(folder/'sample.png')
report={'synthetic_fixtures':True,'accuracy_study':False}
try:
    start=time.perf_counter();ocr=extract_image_text((folder/'sample.png').read_bytes())
    assert 'article' in ocr['ocr_text'].lower()
    report['image']={'passed':True,'seconds':time.perf_counter()-start,'expected_phrase_present':True}
except Exception as exc:report['image']={'passed':False,'error_type':type(exc).__name__,'message':str(exc)}
script="Add-Type -AssemblyName System.Speech; $voice = New-Object System.Speech.Synthesis.SpeechSynthesizer; $voice.SetOutputToWaveFile('"+str(folder/'speech.wav').replace("'","''")+"'); $voice.Speak('Read the full article before sharing. Check the original source.'); $voice.Dispose()"
try:
    subprocess.run(['powershell','-NoProfile','-Command',script],check=True,capture_output=True,timeout=30)
    subprocess.run([ffmpeg_executable(),'-y','-loop','1','-i',str(folder/'sample.png'),'-i',str(folder/'speech.wav'),'-shortest','-c:v','libx264','-pix_fmt','yuv420p',str(folder/'sample.mp4')],capture_output=True,check=True,timeout=60)
    start=time.perf_counter();video=process_video((folder/'sample.mp4').read_bytes())
    assert 'article' in video['transcript_text'].lower() and 'article' in video['frame_ocr_text'].lower()
    report['video']={'passed':True,'seconds':time.perf_counter()-start,'transcript_expected_word':True,'ocr_expected_word':True,'sampled_frames':video['sampled_frames']}
except Exception as exc:report['video']={'passed':False,'error_type':type(exc).__name__,'message':str(exc)}
(ROOT/'docs/MEDIA-VERIFICATION.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
