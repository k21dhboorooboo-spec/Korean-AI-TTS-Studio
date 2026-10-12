import unittest, tempfile, wave, struct
from pathlib import Path
from srt_sync import parse_srt,render
class SRTTests(unittest.TestCase):
 def test_parse(self):
  cues=parse_srt('1\n00:00:01,000 --> 00:00:02,500\n[엄마] 안녕\n\n2\n00:00:03,000 --> 00:00:04,000\n말해')
  self.assertEqual(cues[0],(1000,2500,'엄마','안녕'))
  self.assertEqual(cues[1][2],'나레이터')
 def test_invalid(self):
  with self.assertRaises(ValueError):parse_srt('1\n00:00:61,000 --> 00:00:62,000\n오류')
 def test_render_start_and_overrun(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);wav=t/'voice.wav';out=t/'out.wav'
   with wave.open(str(wav),'wb') as w:
    w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(struct.pack('<h',1000)*8000)
   cues=[(1000,1500,'화자','테스트')]
   warnings=render(cues,[wav],out,rate=8000,max_speed=1.1)
   self.assertTrue(warnings)
   with wave.open(str(out),'rb') as w:
    self.assertEqual(w.getnframes(),16000)
    w.setpos(7999);self.assertEqual(struct.unpack('<h',w.readframes(1))[0],0)
    self.assertEqual(struct.unpack('<h',w.readframes(1))[0],1000)
if __name__=='__main__':unittest.main()
