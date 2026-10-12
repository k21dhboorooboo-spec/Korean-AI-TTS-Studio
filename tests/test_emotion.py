import unittest,sys,tempfile,wave,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from emotion_engine import extract_emotion,settings,adjust_volume
class EmotionTests(unittest.TestCase):
 def test_tag(self):self.assertEqual(extract_emotion('{분노} 그만해!'),('분노','그만해!'))
 def test_default(self):self.assertEqual(extract_emotion('안녕'),('기본','안녕'))
 def test_strength_zero(self):self.assertEqual(settings('분노',0),(1,1))
 def test_invalid(self):
  with self.assertRaises(ValueError):settings('없는감정')
 def test_wav(self):
  with tempfile.TemporaryDirectory() as t:
   a,b=Path(t)/'a.wav',Path(t)/'b.wav'
   with wave.open(str(a),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(struct.pack('<hhh',1000,-1000,20000))
   adjust_volume(a,b,2)
   with wave.open(str(b),'rb') as w:self.assertEqual(struct.unpack('<hhh',w.readframes(3)),(2000,-2000,32767))
if __name__=='__main__':unittest.main()
