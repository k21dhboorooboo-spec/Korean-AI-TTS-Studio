import unittest
from neural_engine import parse_emotion,neural_parameters
class TestNeural(unittest.TestCase):
 def test_tag(self):self.assertEqual(parse_emotion('{분노} 안돼'),('분노','안돼'))
 def test_unknown_tag(self):self.assertEqual(parse_emotion('{외계인} 안돼'),('기본','{외계인} 안돼'))
 def test_range(self):
  for name in ['기쁨','분노','속삭임']:
   for intensity in [-2,0,.5,1,3]:
    p=neural_parameters(name,intensity);self.assertTrue(0<=p['exaggeration']<=1)
