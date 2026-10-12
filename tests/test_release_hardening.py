import unittest, ast, pathlib
from neural_engine import neural_parameters
from srt_sync import parse_srt
class TestHardening(unittest.TestCase):
 def test_emotion_bounds(self):
  for e in ['기쁨','분노','슬픔','기본']:
   for v in [-2,0,0.5,1,10]:
    x=neural_parameters(e,v)['exaggeration'];self.assertTrue(0<=x<=1)
 def test_multilingual_speaker(self):
  cues=parse_srt('1\n00:00:01,000 --> 00:00:02,000\n[JP:母] {슬픔} こんにちは')
  self.assertEqual(cues[0][2],'JP:母')
 def test_gui_compiles(self):
  ast.parse(pathlib.Path(__file__).resolve().parents[1].joinpath('neural_app.py').read_text(encoding='utf-8'))
