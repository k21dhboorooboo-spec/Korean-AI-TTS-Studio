import unittest, tempfile
from pathlib import Path
from voice_clone import convert_voice
class CloneTests(unittest.TestCase):
 def test_missing_configuration_fails_explicitly(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(RuntimeError):convert_voice(Path(d)/'a.wav',Path(d)/'b.wav',Path(d)/'c.wav','KR','auto')
