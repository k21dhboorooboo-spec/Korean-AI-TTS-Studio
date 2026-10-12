import unittest
from emotion_engine import choose_emotion,recommend_emotion
class EmotionRecommendationTest(unittest.TestCase):
 def test_explicit_priority(self): self.assertEqual(choose_emotion('{슬픔} 축하해!',auto=True),('슬픔','축하해!'))
 def test_auto(self): self.assertEqual(recommend_emotion('축하해!'),'기쁨')
 def test_neutral(self): self.assertEqual(choose_emotion('안녕하세요',auto=True),('기본','안녕하세요'))
 def test_disabled(self): self.assertEqual(choose_emotion('축하해!',default='진지함',auto=False),('진지함','축하해!'))
