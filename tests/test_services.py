import tempfile, unittest, wave
from pathlib import Path
from studio_services import VoiceLibrary, AudioCache, inspect_srt, batch_manifest

class ServicesTest(unittest.TestCase):
    def test_library_persists(self):
        with tempfile.TemporaryDirectory() as d:
            a=VoiceLibrary(d);a.put('주인공','KR','KR');self.assertEqual(VoiceLibrary(d).all()['주인공']['voice'],'KR')
    def test_reference_requires_consent(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'voice.wav';p.write_bytes(b'not audio')
            with self.assertRaises(ValueError):VoiceLibrary(d).put('인물','KR',reference=p,consent=False)
    def test_cache_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            a=AudioCache(d);src=Path(d)/'test.wav';dst=Path(d)/'out.wav'
            with wave.open(str(src),'wb') as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(b'\x00\x00'*100)
            k=a.key('안녕','KR','KR',1.0);a.put(k,src)
            self.assertTrue(a.get(k,dst));self.assertEqual(src.read_bytes(),dst.read_bytes())
            self.assertNotEqual(k,a.key('안녕','KR','KR',1.1))
    def test_inspection(self):
        cues=[(0,1000,'나레이터','안녕하세요'),(900,1000,'A','긴 글입니다 테스트')]
        self.assertTrue(any('겹침' in w for w in inspect_srt(cues)))
    def test_batch_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            for n in ('a.srt','b.txt','c.png'): (Path(d)/n).touch()
            self.assertEqual(len(batch_manifest(d)),2)
if __name__=='__main__':unittest.main()
