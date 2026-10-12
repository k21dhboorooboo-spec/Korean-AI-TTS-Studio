import unittest
from neural_app import cue_summary, format_duration

class DashboardTests(unittest.TestCase):
    def test_single(self):
        self.assertEqual(cue_summary('안녕하세요'), (1, 1, False))
    def test_empty(self):
        self.assertEqual(cue_summary(''), (0, 0, False))
    def test_srt(self):
        s = '1\n00:00:00,000 --> 00:00:02,000\n[KR:민호] 안녕\n\n2\n00:00:02,000 --> 00:00:04,000\n[KR:서연] 반가워'
        self.assertEqual(cue_summary(s), (2, 2, True))
    def test_time(self):
        self.assertEqual(format_duration(125), '2분 5초')
        self.assertEqual(format_duration(0), '0초')
