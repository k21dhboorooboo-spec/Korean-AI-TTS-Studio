"""Local voice library, deterministic cache and SRT quality reports. Stdlib only."""
import hashlib, json, os, re, shutil, sqlite3, tempfile, wave
from pathlib import Path

APP_DATA = Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local' / 'share')) / 'KoreanAITTSStudio'

class VoiceLibrary:
    def __init__(self, root=APP_DATA):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.db=self.root/'voices.sqlite3'
        with sqlite3.connect(self.db) as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS voices (name TEXT PRIMARY KEY, language TEXT NOT NULL, voice TEXT NOT NULL, reference TEXT, consent INTEGER NOT NULL DEFAULT 0)')
    def put(self,name,language,voice='자동',reference=None,consent=False):
        if not name.strip() or language not in ('KR','EN','JP'): raise ValueError('화자 이름/언어 오류')
        if reference and (not consent or not Path(reference).is_file()): raise ValueError('샘플 파일 및 사용 권한을 확인하세요')
        with sqlite3.connect(self.db) as conn:
            conn.execute('INSERT OR REPLACE INTO voices VALUES(?,?,?,?,?)',(name.strip(),language,voice,str(Path(reference).resolve()) if reference else None,int(consent)))
    def all(self):
        with sqlite3.connect(self.db) as conn:
            return {n:dict(language=l,voice=v,**({'reference_wav':r,'consent':bool(c)} if r else {})) for n,l,v,r,c in conn.execute('SELECT * FROM voices')}

class AudioCache:
    def __init__(self,root=APP_DATA):
        self.root=Path(root)/'cache';self.root.mkdir(parents=True,exist_ok=True)
    def key(self, text, language, voice, speed, reference=None, engine='MeloTTS+OpenVoiceV2'):
        ref_sig=None
        if reference:
            p=Path(reference)
            if not p.is_file():raise FileNotFoundError(p)
            ref_sig={'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        data={'text':text,'language':language,'voice':voice,'speed':round(float(speed),4),'reference':ref_sig,'engine':engine}
        return hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    def get(self,key,target):
        p=self.root/(key+'.wav')
        if not p.is_file():return False
        try:
            with wave.open(str(p),'rb') as w:
                if w.getnframes()==0: return False
        except (wave.Error,EOFError):return False
        shutil.copy2(p,target);return True
    def put(self,key,source):
        with wave.open(str(source),'rb') as w:
            if w.getnframes()==0:raise ValueError('빈 음성은 캐시에 저장하지 않습니다')
        dst=self.root/(key+'.wav')
        fd,tmp=tempfile.mkstemp(dir=self.root,suffix='.wav');os.close(fd)
        try:shutil.copy2(source,tmp);os.replace(tmp,dst)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

def inspect_srt(cues):
    warnings=[]; previous_end=0
    for i,(start,end,speaker,text) in enumerate(cues,1):
        if start<previous_end:warnings.append(f'{i}번: 이전 자막과 {previous_end-start}ms 겹침')
        if end-start<350:warnings.append(f'{i}번: 음성 구간이 0.35초 미만')
        if len(text)/max((end-start)/1000,0.001)>9:warnings.append(f'{i}번: 글자 수 대비 시간이 짧을 수 있음 ({len(text)}자/{(end-start)/1000:.1f}초)')
        if not speaker.strip():warnings.append(f'{i}번: 화자 이름 없음')
        previous_end=max(previous_end,end)
    return warnings

def batch_manifest(folder):
    folder=Path(folder)
    if not folder.is_dir():raise NotADirectoryError(folder)
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in ('.srt','.txt'))
