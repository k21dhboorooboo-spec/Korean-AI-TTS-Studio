import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
import threading,json,re
from neural_engine import NeuralTTS,EMOTIONS,parse_emotion
from srt_sync import parse_srt,render
from tempfile import TemporaryDirectory

class App:
 def __init__(self,root):
  self.root=root;root.title('KOREAN AI TTS STUDIO v1.2 · Neural Emotion (CPU)');root.geometry('850x680')
  self.engine=NeuralTTS();self.language=tk.StringVar(value='KR');self.emotion=tk.StringVar(value='기본');self.strength=tk.DoubleVar(value=0.7);self.ref=tk.StringVar();self.voice_map=tk.StringVar();self.status=tk.StringVar(value='신경망 엔진 설치 및 첫 모델 다운로드가 필요합니다.')
  frame=ttk.Frame(root,padding=15);frame.pack(fill='both',expand=True)
  ttk.Label(frame,text='신경망 감정 TTS · 한국어 / 영어 / 일본어',font=('Malgun Gothic',16,'bold')).pack(anchor='w')
  row=ttk.Frame(frame);row.pack(fill='x',pady=8)
  ttk.Label(row,text='언어').pack(side='left');ttk.Combobox(row,textvariable=self.language,values=['KR','EN','JP'],state='readonly',width=6).pack(side='left',padx=6)
  ttk.Label(row,text='감정').pack(side='left');ttk.Combobox(row,textvariable=self.emotion,values=list(EMOTIONS),state='readonly',width=12).pack(side='left',padx=6)
  ttk.Label(row,text='표현 강도').pack(side='left');ttk.Scale(row,from_=0,to=1,variable=self.strength,length=170).pack(side='left',padx=6)
  row2=ttk.Frame(frame);row2.pack(fill='x',pady=8)
  ttk.Button(row2,text='허가된 참조 음성 선택',command=self.pick_ref).pack(side='left');ttk.Label(row2,textvariable=self.ref,wraplength=560).pack(side='left',padx=8)
  ttk.Button(row2,text='화자별 음성 JSON 선택',command=self.pick_voice_map).pack(side='left',padx=6)
  ttk.Label(frame,text='TXT 또는 SRT 붙여넣기. SRT: [KR:나레이터] {분노} 대사 / [JP:母] {슬픔} 대사').pack(anchor='w')
  self.editor=tk.Text(frame,font=('Malgun Gothic',11),wrap='word');self.editor.pack(fill='both',expand=True,pady=8)
  self.editor.insert('1.0','[나레이터] {기쁨} 안녕하세요. 오늘은 특별한 이야기를 들려드리겠습니다.')
  bar=ttk.Frame(frame);bar.pack(fill='x')
  ttk.Button(bar,text='TXT/SRT 불러오기',command=self.load).pack(side='left',padx=3)
  self.btn=ttk.Button(bar,text='감정 음성 생성 WAV',command=self.start);self.btn.pack(side='left',padx=3)
  ttk.Label(frame,textvariable=self.status,wraplength=800).pack(anchor='w',pady=12)
  ttk.Label(frame,text='감정별 연기 품질은 모델·참조 음성·대본에 따라 달라집니다. CPU 생성은 오래 걸릴 수 있습니다.',foreground='#555').pack(anchor='w')
 def pick_ref(self):
  p=filedialog.askopenfilename(filetypes=[('Audio','*.wav *.mp3')]);
  if p:self.ref.set(p)
 def pick_voice_map(self):
  p=filedialog.askopenfilename(filetypes=[('JSON','*.json')]);
  if p:self.voice_map.set(p);self.status.set('화자 음성 설정: '+p)
 def load(self):
  p=filedialog.askopenfilename(filetypes=[('Scripts','*.txt *.srt')]);
  if p:self.editor.delete('1.0','end');self.editor.insert('1.0',Path(p).read_text(encoding='utf-8-sig'))
 def start(self):
  data=self.editor.get('1.0','end').strip()
  if not data:return
  out=filedialog.asksaveasfilename(defaultextension='.wav',filetypes=[('WAV','*.wav')]);
  if not out:return
  self.btn.config(state='disabled');self.status.set('생성 중: CPU에서는 시간이 걸립니다.')
  threading.Thread(target=self.work,args=(data,out,self.language.get(),self.emotion.get(),self.strength.get(),self.ref.get(),self.voice_map.get()),daemon=True).start()
 def work(self,data,out,lang,emotion,strength,reference,voice_map_path):
  try:
   voice_map={}
   if voice_map_path:
    voice_map=json.loads(Path(voice_map_path).read_text(encoding='utf-8-sig'))
    if not isinstance(voice_map,dict):raise ValueError('화자별 음성 JSON은 객체여야 합니다')
    for name,path in voice_map.items():
     if not isinstance(name,str) or not isinstance(path,str) or not Path(path).is_file():
      raise ValueError('화자별 음성 경로가 유효하지 않습니다: '+str(name))
   if '-->' in data:
    cues=parse_srt(data);voices={};warnings=[]
    with TemporaryDirectory() as temp:
     files=[]
     for i,(start,end,speaker,line) in enumerate(cues):
      m=re.match(r'^(KR|EN|JP):(.+)$',speaker,re.I);cue_lang=m.group(1).upper() if m else lang
      cue_emotion,clean=parse_emotion(line,emotion)
      path=Path(temp)/f'{i:05d}.wav'
      voice_ref=voice_map.get(speaker,voice_map.get(m.group(2) if m else speaker,reference or None))
      self.engine.generate(clean,path,cue_lang,cue_emotion,strength,voice_ref);files.append(path)
     warnings=render(cues,files,out,rate=24000,max_speed=1.0,overflow='warn')
    Path(out+'.sync_report.txt').write_text('\n'.join(warnings) if warnings else '싱크 초과 경고 없음',encoding='utf-8')
   else:
    text=re.sub(r'^\s*\[[^]]+\]\s*','',data);cue_emotion,clean=parse_emotion(text,emotion)
    self.engine.generate(clean,out,lang,cue_emotion,strength,voice_map.get('나레이터',reference or None))
   self.root.after(0,lambda:self.status.set('완료: '+out))
  except Exception as e:self.root.after(0,lambda msg=str(e):self.status.set('오류: '+msg))
  finally:self.root.after(0,lambda:self.btn.config(state='normal'))
if __name__=='__main__':
 root=tk.Tk();App(root);root.mainloop()
