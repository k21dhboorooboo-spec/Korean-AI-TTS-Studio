"""Transparent CPU-only emotion approximations; not neural emotional acting."""
import re, wave, array, sys
from pathlib import Path
EMOTIONS={
 '기본':(1.00,1.00),'기쁨':(1.07,1.10),'슬픔':(0.92,0.83),
 '분노':(1.08,1.17),'놀람':(1.12,1.08),'공포':(1.04,0.85),
 '속삭임':(0.94,0.58),'진지함':(0.95,0.95),'다정함':(0.96,0.88),
 '긴박함':(1.14,1.08)}
TAG=re.compile(r'^\s*\{(기본|기쁨|슬픔|분노|놀람|공포|속삭임|진지함|다정함|긴박함)\}\s*')
def extract_emotion(text,default='기본'):
 m=TAG.match(text)
 return (m.group(1),text[m.end():]) if m else (default,text)
def settings(name,intensity=0.6):
 if name not in EMOTIONS: raise ValueError('알 수 없는 감정: '+str(name))
 strength=max(0.0,min(1.0,float(intensity)))
 s,g=EMOTIONS[name]
 return 1+(s-1)*strength, 1+(g-1)*strength

def adjust_volume(source,target,gain):
 """16-bit PCM WAV gain, preserve format and frame count."""
 with wave.open(str(source),'rb') as w:
  params=w.getparams()
  if w.getsampwidth()!=2 or w.getcomptype()!='NONE': raise ValueError('16-bit PCM WAV 필요')
  data=w.readframes(w.getnframes())
 a=array.array('h');a.frombytes(data)
 if sys.byteorder!='little':a.byteswap()
 for i,v in enumerate(a):a[i]=max(-32768,min(32767,round(v*gain)))
 if sys.byteorder!='little':a.byteswap()
 with wave.open(str(target),'wb') as w:w.setparams(params);w.writeframes(a.tobytes())


def recommend_emotion(text):
 """Conservative, deterministic keyword-based suggestion; not AI sentiment understanding."""
 t=text.strip()
 if not t: return '기본'
 if any(x in t for x in ('살려줘','도와줘!','무서워','怖い','助けて','help me')): return '공포'
 if any(x in t for x in ('빨리!','서둘러','急いで','hurry up')): return '긴박함'
 if any(x in t for x in ('화가 나','용서 못','닥쳐','ふざけるな','shut up')): return '분노'
 if any(x in t for x in ('슬퍼','눈물이','悲しい','so sad')): return '슬픔'
 if any(x in t for x in ('정말?','뭐라고?','えっ','really?')): return '놀람'
 if any(x in t for x in ('축하해','행복해','おめでとう','congratulations')): return '기쁨'
 return '기본'

def choose_emotion(text,default='기본',auto=False):
 explicit,clean=extract_emotion(text,default)
 if clean!=text: return explicit,clean
 return (recommend_emotion(clean) if auto else default),clean
