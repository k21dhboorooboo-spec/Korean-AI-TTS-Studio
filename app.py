import os, re, sys, wave, shutil, subprocess, threading, tempfile, json
from studio_services import VoiceLibrary, AudioCache, inspect_srt, batch_manifest
from emotion_engine import EMOTIONS, extract_emotion, settings, adjust_volume
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

BASE = Path(__file__).resolve().parent

# Presets affect pacing and sync policy. Emotion profiles approximate delivery via speed and volume.
PRESETS = {
    '쇼츠': {'speed': 1.15, 'gap': 110, 'max_sync_speed': 1.20},
    '롱폼': {'speed': 0.98, 'gap': 350, 'max_sync_speed': 1.12},
    '다큐멘터리': {'speed': 0.92, 'gap': 400, 'max_sync_speed': 1.12},
    '드라마': {'speed': 1.00, 'gap': 260, 'max_sync_speed': 1.15},
    '쇼핑·광고': {'speed': 1.18, 'gap': 100, 'max_sync_speed': 1.22},
    '역사·스토리': {'speed': 0.95, 'gap': 420, 'max_sync_speed': 1.12},
    '사용자 설정': {'speed': 1.00, 'gap': 220, 'max_sync_speed': 1.15},
}



def split_text(text, limit=180):
    parts = re.split(r'(?<=[.!?。！？])\s+|\n+', text.strip())
    out = []
    for part in parts:
        part = part.strip()
        while len(part) > limit:
            idx = max(part.rfind(' ', 0, limit), part.rfind(',', 0, limit), part.rfind('，', 0, limit))
            if idx < limit // 3: idx = limit
            out.append(part[:idx].strip())
            part = part[idx:].strip()
        if part: out.append(part)
    return out


def combine_wav(paths, target, silence_ms=220):
    with wave.open(str(paths[0]), 'rb') as first:
        params = first.getparams()
    with wave.open(str(target), 'wb') as output:
        output.setparams(params)
        for i, path in enumerate(paths):
            with wave.open(str(path), 'rb') as src:
                if (src.getnchannels(), src.getsampwidth(), src.getframerate(), src.getcomptype()) != (params.nchannels, params.sampwidth, params.framerate, params.comptype):
                    raise ValueError('생성된 WAV 형식이 일치하지 않습니다.')
                output.writeframes(src.readframes(src.getnframes()))
            if i < len(paths)-1:
                frames = int(params.framerate * silence_ms / 1000)
                output.writeframes(b'\x00' * frames * params.nchannels * params.sampwidth)

class Studio:
    def __init__(self, root):
        self.root = root
        root.title('KOREAN AI TTS STUDIO v0.9 · Emotion & SRT')
        root.geometry('860x730')
        self.status = tk.StringVar(value='준비됨 · 첫 생성 시 모델 다운로드를 위해 인터넷이 필요할 수 있습니다.')
        self.speed = tk.DoubleVar(value=1.0)
        self.gap = tk.IntVar(value=220)
        self.preset = tk.StringVar(value='롱폼')
        self.last_file = None
        self.models = {}
        self.library=VoiceLibrary()
        self.cache=AudioCache()
        self.voice_map = self.library.all()
        self.reference_voices = {}
        self.language = tk.StringVar(value='KR')
        self.voice = tk.StringVar(value='자동')
        self.emotion = tk.StringVar(value='기본')
        self.emotion_strength = tk.DoubleVar(value=0.6)
        self.auto_emotion = tk.BooleanVar(value=False)
        self.busy = False
        main = ttk.Frame(root, padding=20)
        main.pack(fill='both', expand=True)
        ttk.Label(main, text='KOREAN AI TTS STUDIO', font=('Malgun Gothic', 19, 'bold')).pack(anchor='w')
        ttk.Label(main, text='한국어·영어·일본어 로컬 음성 합성 · CPU · 모델별 실제 음성 목록 확인').pack(anchor='w', pady=(0,14))
        preset_row = ttk.Frame(main); preset_row.pack(fill='x', pady=(0, 10))
        ttk.Label(preset_row, text='콘텐츠 제작 모드').pack(side='left', padx=(0, 10))
        self.preset_box = ttk.Combobox(preset_row, state='readonly', textvariable=self.preset,
                                        values=list(PRESETS), width=19)
        self.preset_box.pack(side='left')
        self.preset_box.bind('<<ComboboxSelected>>', self.apply_preset)
        ttk.Button(preset_row, text='설정 JSON 저장', command=self.save_preset).pack(side='left', padx=8)
        ttk.Button(preset_row, text='설정 JSON 불러오기', command=self.load_preset).pack(side='left')
        ttk.Label(main, text='모드는 속도·쉼·SRT 길이 조절 한도를 설정합니다. 음색·감정은 변경하지 않습니다.', foreground='#555').pack(anchor='w', pady=(0, 8))
        voice_row=ttk.Frame(main);voice_row.pack(fill='x',pady=(0,10))
        ttk.Label(voice_row,text='기본 언어').pack(side='left')
        self.language_box=ttk.Combobox(voice_row,textvariable=self.language,state='readonly',values=['KR','EN','JP'],width=7)
        self.language_box.pack(side='left',padx=6)
        self.language_box.bind('<<ComboboxSelected>>',lambda e:self.refresh_voices())
        ttk.Label(voice_row,text='기본 음성').pack(side='left',padx=(12,0))
        self.voice_box=ttk.Combobox(voice_row,textvariable=self.voice,state='readonly',values=['자동'],width=23)
        self.voice_box.pack(side='left',padx=6)
        ttk.Button(voice_row,text='모델 음성 목록 확인',command=self.refresh_voices).pack(side='left',padx=6)
        ttk.Button(voice_row,text='화자별 음성 지정',command=self.edit_voice_map).pack(side='left')
        ttk.Button(voice_row,text='허가 음성 샘플 등록',command=self.register_reference).pack(side='left',padx=6)
        emotion_row=ttk.Frame(main);emotion_row.pack(fill='x',pady=(0,8))
        ttk.Label(emotion_row,text='감정 선택').pack(side='left')
        ttk.Combobox(emotion_row,textvariable=self.emotion,state='readonly',values=list(EMOTIONS),width=12).pack(side='left',padx=6)
        ttk.Label(emotion_row,text='감정 강도').pack(side='left',padx=(14,4))
        ttk.Scale(emotion_row,from_=0,to=1,variable=self.emotion_strength,orient='horizontal',length=140).pack(side='left')
        ttk.Checkbutton(emotion_row,text='대사 감정 자동 추천',variable=self.auto_emotion).pack(side='left',padx=8)
        ttk.Label(main,text='감정은 속도·음량 기반 근사 연출이며, 실제 감정 연기 모델은 아닙니다.',foreground='#555').pack(anchor='w')
        ttk.Label(main,text='SRT 화자: [며느리] 대사 / 언어 지정: [EN:John] Hello / [JP:母] こんにちは',foreground='#555').pack(anchor='w')
        self.editor = tk.Text(main, height=15, wrap='word', font=('Malgun Gothic', 11), undo=True)
        self.editor.pack(fill='both', expand=True)
        self.editor.insert('1.0', '안녕하세요. 한국어 인공지능 음성 합성 프로그램입니다. 오늘은 새로운 이야기를 시작하겠습니다.')
        row = ttk.Frame(main); row.pack(fill='x', pady=12)
        ttk.Label(row, text='말하기 속도').pack(side='left')
        ttk.Scale(row, from_=0.75, to=1.3, variable=self.speed, orient='horizontal', length=170).pack(side='left', padx=10)
        ttk.Label(row, textvariable=self.speed).pack(side='left')
        ttk.Label(row, text='   문장 간 쉼(ms)').pack(side='left', padx=(25,5))
        ttk.Spinbox(row, from_=0, to=1500, increment=50, textvariable=self.gap, width=7).pack(side='left')
        buttons = ttk.Frame(main); buttons.pack(fill='x', pady=6)
        self.generate_btn = ttk.Button(buttons, text='음성 생성 및 저장', command=self.generate)
        self.generate_btn.pack(side='left', padx=(0,8))
        ttk.Button(buttons, text='미리듣기', command=self.play).pack(side='left', padx=5)
        ttk.Button(buttons, text='SRT 불러오기', command=self.load_srt).pack(side='left', padx=5)
        ttk.Button(buttons, text='SRT 싱크 음성 생성', command=self.generate_srt).pack(side='left', padx=5)
        ttk.Button(buttons, text='TXT 불러오기', command=self.load_text).pack(side='left', padx=5)
        ttk.Button(buttons, text='폴더 일괄 처리', command=self.batch_generate).pack(side='left', padx=5)
        ttk.Button(buttons, text='내용 지우기', command=lambda: self.editor.delete('1.0','end')).pack(side='left', padx=5)
        ttk.Separator(main).pack(fill='x', pady=12)
        self.apply_preset()
        ttk.Label(main, textvariable=self.status, wraplength=710).pack(anchor='w')
        ttk.Label(main, text='첫 실행: 모델 파일 다운로드 필요 | 이후 캐시가 있으면 오프라인 사용 가능 | MP3 저장은 ffmpeg 필요', foreground='#666').pack(anchor='w', pady=10)

    def get_model(self,language):
        if language not in ('KR','EN','JP'): raise ValueError('지원하지 않는 언어: '+language)
        if language not in self.models:
            from melo.api import TTS
            self.report(f'{language} 모델 불러오는 중...')
            self.models[language]=TTS(language=language,device='cpu')
        return self.models[language]

    def available_voices(self,language):
        return list(self.get_model(language).hps.data.spk2id.keys())

    def refresh_voices(self):
        lang=self.language.get()
        def task():
            try:
                voices=self.available_voices(lang)
                self.root.after(0,lambda:self._set_voices(voices))
            except Exception as e:
                self.root.after(0,lambda msg=str(e):messagebox.showerror('모델 오류',msg))
        threading.Thread(target=task,daemon=True).start()

    def _set_voices(self,voices):
        self.voice_box.configure(values=['자동']+voices)
        self.voice.set('자동')
        self.report('사용 가능한 음성: '+', '.join(voices))

    def edit_voice_map(self):
        window=tk.Toplevel(self.root);window.title('등장인물 음성 설정 JSON');window.geometry('640x380')
        ttk.Label(window,text='화자 이름을 언어/모델 음성에 매핑합니다. 음성 이름은 모델 목록 확인 후 입력하세요.').pack(anchor='w',padx=12,pady=8)
        editor=tk.Text(window,font=('Consolas',10));editor.pack(fill='both',expand=True,padx=12)
        editor.insert('1.0',json.dumps(self.voice_map or {'나레이터':{'language':'KR','voice':'자동'},'John':{'language':'EN','voice':'자동'},'母':{'language':'JP','voice':'자동'}},ensure_ascii=False,indent=2))
        def save():
            try:
                data=json.loads(editor.get('1.0','end'))
                if not isinstance(data,dict):raise ValueError('JSON 객체여야 합니다')
                for who,config in data.items():
                    if not isinstance(config,dict) or config.get('language','KR') not in ('KR','EN','JP') or not isinstance(config.get('voice','자동'),str):raise ValueError('잘못된 화자 설정: '+str(who))
                self.voice_map=data
                for person, cfg in data.items():
                    self.library.put(person,cfg.get('language','KR'),cfg.get('voice','자동'),cfg.get('reference_wav'),cfg.get('consent',False))
                window.destroy()
            except Exception as e:messagebox.showerror('설정 오류',str(e))
        ttk.Button(window,text='적용',command=save).pack(pady=8)

    def resolve_voice(self,speaker,default_language,default_voice):
        lang=default_language;name=speaker
        m=re.match(r'^(KR|EN|JP)\s*:\s*(.+)$',speaker,re.I)
        if m:lang=m.group(1).upper();name=m.group(2).strip()
        config=self.voice_map.get(name,self.voice_map.get(speaker,{}))
        lang=config.get('language',lang)
        voice=config.get('voice','자동')
        if voice=='자동' and lang==default_language:voice=default_voice
        model=self.get_model(lang)
        speakers=model.hps.data.spk2id
        if voice=='자동':voice=next(iter(speakers))
        if voice not in speakers:raise ValueError(f'{speaker}: {lang} 모델에 {voice} 음성이 없습니다. 가능한 음성: {list(speakers)}')
        return model,speakers[voice]

    def register_reference(self):
        from tkinter import simpledialog
        person=simpledialog.askstring('허가 음성 등록','등장인물 이름을 입력하세요 (예: 며느리):',parent=self.root)
        if not person: return
        path=filedialog.askopenfilename(title='사용 권한이 있는 음성 샘플',filetypes=[('WAV 오디오','*.wav')])
        if not path:return
        if not messagebox.askyesno('사용 권한 확인','이 음성은 본인의 목소리이거나 명시적인 사용 허가를 받은 음성입니까?\n권한 없는 인물의 음성을 복제하지 마세요.'):
            return
        self.reference_voices[person]=path
        self.voice_map[person]={'language':self.language.get(),'voice':'자동','reference_wav':path,'consent':True}
        self.library.put(person,self.language.get(),'자동',path,True)
        self.report(f'참조 음성 등록: {person} / OpenVoice V2 설정 후 사용 가능')

    def postprocess_reference(self,speaker,base_wav,output_wav,language,voice):
        config=voice_map.get(speaker,voice_map.get(speaker.split(':',1)[-1],{}))
        ref=config.get('reference_wav')
        if not ref:return base_wav
        if not config.get('consent'):
            raise ValueError(f'{speaker}: 음성 사용 권한 확인이 필요합니다.')
        from voice_clone import convert_voice
        convert_voice(base_wav,ref,output_wav,language,voice)
        return output_wav

    def apply_preset(self, event=None):
        values = PRESETS[self.preset.get()]
        self.speed.set(values['speed'])
        self.gap.set(values['gap'])

    def save_preset(self):
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON','*.json')])
        if not path: return
        payload = {'preset': self.preset.get(), 'speed': float(self.speed.get()),
                   'gap_ms': int(self.gap.get()), 'version': '0.9'}
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        self.status.set('설정 저장: ' + path)

    def load_preset(self):
        path = filedialog.askopenfilename(filetypes=[('JSON','*.json')])
        if not path: return
        try:
            data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
            preset = data['preset']
            if preset not in PRESETS: raise ValueError('알 수 없는 제작 모드입니다.')
            speed = float(data['speed']); gap = int(data['gap_ms'])
            if not 0.75 <= speed <= 1.3 or not 0 <= gap <= 1500:
                raise ValueError('속도 또는 쉼 값이 허용 범위를 벗어났습니다.')
            self.preset.set(preset); self.speed.set(speed); self.gap.set(gap)
            self.status.set('설정 불러옴: ' + path)
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as e:
            messagebox.showerror('설정 오류', str(e))

    def load_text(self):
        path = filedialog.askopenfilename(filetypes=[('Text files','*.txt'),('All files','*.*')])
        if path:
            try:
                content = Path(path).read_text(encoding='utf-8-sig')
            except UnicodeDecodeError:
                content = Path(path).read_text(encoding='cp949')
            self.editor.delete('1.0','end'); self.editor.insert('1.0',content)

    def load_srt(self):
        path = filedialog.askopenfilename(filetypes=[('SRT 자막','*.srt')])
        if path:
            try:
                data=Path(path).read_text(encoding='utf-8-sig')
            except UnicodeDecodeError:
                data=Path(path).read_text(encoding='cp949')
            self.editor.delete('1.0','end'); self.editor.insert('1.0',data)
            self.status.set('SRT 불러옴: '+path)

    def generate_srt(self):
        from srt_sync import parse_srt
        content=self.editor.get('1.0','end').strip()
        try: cues=parse_srt(content)
        except Exception as e: messagebox.showerror('SRT 오류',str(e)); return
        path=filedialog.asksaveasfilename(defaultextension='.wav',filetypes=[('WAV','*.wav'),('MP3','*.mp3')],initialfile='srt_synced.wav')
        if not path: return
        if self.busy:
            messagebox.showwarning('안내','이미 음성을 생성 중입니다.'); return
        self.busy=True; self.generate_btn.configure(state='disabled')
        mode=self.preset.get()
        threading.Thread(target=self.srt_worker,args=(cues,Path(path),float(self.speed.get()),mode,self.language.get(),self.voice.get(),dict(self.voice_map),False,self.emotion.get(),float(self.emotion_strength.get()),self.auto_emotion.get()),daemon=True).start()

    def srt_worker(self,cues,path,speed,mode,language,voice,voice_map,batch=False,emotion='기본',strength=0.6,auto_emotion=False):
        from srt_sync import render
        from emotion_engine import choose_emotion
        try:
            with tempfile.TemporaryDirectory() as temp:
                wavs=[]
                for i,(_,_,speaker,text) in enumerate(cues,1):
                    cue_emotion, text = choose_emotion(text,emotion,auto_emotion)
                    emo_speed, emo_gain = settings(cue_emotion,strength)
                    self.report(f'SRT 음성 생성 {i}/{len(cues)}: {speaker}')
                    wav=Path(temp)/f'cue_{i:05d}.wav'
                    model,speaker_id=self.resolve_voice(speaker,language,voice)
                    config=voice_map.get(speaker,voice_map.get(speaker.split(':',1)[-1],{}))
                    lang=config.get('language',speaker.split(':',1)[0].upper() if ':' in speaker and speaker.split(':',1)[0].upper() in ('KR','EN','JP') else language)
                    selected=config.get('voice',voice if lang==language else '자동')
                    if selected=='자동': selected=next(k for k,v in model.hps.data.spk2id.items() if v==speaker_id)
                    ref=config.get('reference_wav')
                    key=self.cache.key(text,lang,selected,speed*emo_speed,ref,engine='MeloTTS+OpenVoiceV2+emotion:'+cue_emotion+':'+str(strength))
                    if not self.cache.get(key,wav):
                        raw=Path(temp)/f'raw_{i:05d}.wav'
                        model.tts_to_file(text,speaker_id,str(raw),speed=speed*emo_speed)
                        gained=Path(temp)/f'gain_{i:05d}.wav'
                        adjust_volume(raw,gained,emo_gain)
                        raw=gained
                        processed=Path(temp)/f'processed_{i:05d}.wav'
                        final=self.postprocess_reference(speaker,raw,processed,lang,selected)
                        shutil.copy2(final,wav)
                        self.cache.put(key,wav)
                    wavs.append(wav)
                combined=Path(temp)/'synced.wav'
                clean_cues=[(a,b,c,choose_emotion(t,emotion,auto_emotion)[1]) for a,b,c,t in cues]
                warnings=inspect_srt(clean_cues)+render(clean_cues,wavs,combined,max_speed=PRESETS[mode]['max_sync_speed'])
                path.parent.mkdir(parents=True,exist_ok=True)
                if path.suffix.lower()=='.mp3':
                    ffmpeg=shutil.which('ffmpeg')
                    if not ffmpeg: raise RuntimeError('MP3 저장은 ffmpeg 설치가 필요합니다. WAV로 저장하세요.')
                    subprocess.run([ffmpeg,'-y','-loglevel','error','-i',str(combined),'-codec:a','libmp3lame','-qscale:a','2',str(path)],check=True)
                else: shutil.copy2(combined,path)
            report=path.with_suffix('.sync_report.txt')
            report.write_text('SRT 동기화 결과 (콘텐츠 모드: '+mode+')\n'+'\n'.join(warnings or ['경고 없음'])+'\n',encoding='utf-8-sig')
            self.last_file=path
            self.report(f'완료: {path} / 경고 {len(warnings)}건')
            if not batch:self.root.after(0,lambda p=path,n=len(warnings),r=report:messagebox.showinfo('완료',f'저장: {p}\n싱크 경고: {n}건\n리포트: {r}'))
        except Exception as e:
            msg=str(e);self.report('오류: '+msg)
            if batch:raise
            self.root.after(0,lambda m=msg:messagebox.showerror('실패',m))
        finally:
            if not batch:self.root.after(0,self.finish)

    def batch_generate(self):
        if self.busy:
            messagebox.showwarning('안내','이미 작업 중입니다.');return
        folder=filedialog.askdirectory(title='TXT/SRT 파일 폴더 선택')
        if not folder:return
        files=batch_manifest(folder)
        if not files:
            messagebox.showwarning('안내','TXT 또는 SRT 파일이 없습니다.');return
        out=filedialog.askdirectory(title='출력 폴더 선택')
        if not out:return
        self.busy=True;self.generate_btn.configure(state='disabled')
        def task():
            results=[]
            for index,src in enumerate(files,1):
                try:
                    self.report(f'일괄 처리 {index}/{len(files)}: {src.name}')
                    try: content=src.read_text(encoding='utf-8-sig')
                    except UnicodeDecodeError: content=src.read_text(encoding='cp949')
                    target=Path(out)/(src.stem+'.wav')
                    if src.suffix.lower()=='.srt':
                        from srt_sync import parse_srt
                        cues=parse_srt(content)
                        self.srt_worker(cues,target,float(self.speed.get()),self.preset.get(),self.language.get(),self.voice.get(),dict(self.voice_map),batch=True,emotion=self.emotion.get(),strength=float(self.emotion_strength.get()),auto_emotion=self.auto_emotion.get())
                    else:
                        self.worker(content,target,float(self.speed.get()),int(self.gap.get()),self.language.get(),self.voice.get(),batch=True)
                    results.append(src.name+': 성공' if target.is_file() and target.stat().st_size>44 else src.name+': 실패 - 출력 파일 없음')
                except Exception as exc:results.append(src.name+': 실패 '+str(exc))
            (Path(out)/'batch_report.txt').write_text('\n'.join(results),encoding='utf-8-sig')
            self.root.after(0,self.finish)
        threading.Thread(target=task,daemon=True).start()

    def finish(self):
        self.busy=False
        self.generate_btn.configure(state="normal")

    def play(self):
        if not self.last_file or not self.last_file.exists():
            messagebox.showinfo('안내', '먼저 음성을 생성해 주세요.'); return
        os.startfile(str(self.last_file))

    def generate(self):
        content = self.editor.get('1.0','end').strip()
        if not content:
            messagebox.showwarning('안내','대본을 입력하세요.'); return
        path = filedialog.asksaveasfilename(defaultextension='.wav', filetypes=[('WAV 오디오','*.wav'),('MP3 오디오','*.mp3')], initialfile='narration.wav')
        if not path: return
        speed = float(self.speed.get()); gap = int(self.gap.get())
        if self.busy:
            messagebox.showwarning('안내','이미 음성을 생성 중입니다.'); return
        self.busy=True; self.generate_btn.configure(state='disabled')
        threading.Thread(target=self.worker, args=(content, Path(path), speed, gap,self.language.get(),self.voice.get()), daemon=True).start()

    def report(self, message):
        self.root.after(0, lambda m=message: self.status.set(m))

    def worker(self, content, path, speed, gap,language,voice,batch=False):
        try:
            model,speaker_id=self.resolve_voice('나레이터',language,voice)
            chunks = split_text(content)
            if not chunks: raise ValueError('변환할 문장이 없습니다.')
            with tempfile.TemporaryDirectory() as temp:
                wavs=[]
                for i, chunk in enumerate(chunks, 1):
                    self.report(f'음성 생성 중... {i}/{len(chunks)} 문장')
                    wav = Path(temp)/f'chunk_{i:04d}.wav'
                    cfg=self.voice_map.get('나레이터',{})
                    emo_speed,emo_gain=settings(self.emotion.get(),self.emotion_strength.get())
                    key=self.cache.key(chunk,language,voice,speed*emo_speed,cfg.get('reference_wav'),engine='MeloTTS+OpenVoiceV2+emotion:'+self.emotion.get()+':'+str(self.emotion_strength.get()))
                    if not self.cache.get(key,wav):
                        raw=Path(temp)/f'raw_{i:04d}.wav'
                        model.tts_to_file(chunk,speaker_id,str(raw),speed=speed*emo_speed)
                        gained=Path(temp)/f'gain_{i:05d}.wav'
                        adjust_volume(raw,gained,emo_gain)
                        raw=gained
                        processed=Path(temp)/f'processed_{i:04d}.wav'
                        final=self.postprocess_reference('나레이터',raw,processed,language,voice)
                        shutil.copy2(final,wav)
                        self.cache.put(key,wav)
                    wavs.append(wav)
                combined = Path(temp)/'combined.wav'
                combine_wav(wavs, combined, gap)
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.suffix.lower() == '.mp3':
                    ffmpeg = shutil.which('ffmpeg')
                    if not ffmpeg: raise RuntimeError('MP3 변환에는 ffmpeg가 필요합니다. WAV로 저장하거나 ffmpeg를 설치하세요.')
                    subprocess.run([ffmpeg,'-y','-loglevel','error','-i',str(combined),'-codec:a','libmp3lame','-qscale:a','2',str(path)],check=True)
                else:
                    shutil.copy2(combined,path)
            self.last_file=path
            self.report(f'완료: {path}')
            if not batch:self.root.after(0, lambda p=path: messagebox.showinfo('완료',f'음성 저장 완료!\n{p}'))
        except Exception as e:
            msg=str(e)
            self.report('오류: '+msg)
            if batch:raise
            self.root.after(0, lambda m=msg: messagebox.showerror('음성 생성 실패', m))
        finally:
            if not batch:self.root.after(0, self.finish)

if __name__ == '__main__':
    root=tk.Tk()
    try:
        style=ttk.Style(); style.theme_use('clam')
    except tk.TclError: pass
    Studio(root)
    root.mainloop()
