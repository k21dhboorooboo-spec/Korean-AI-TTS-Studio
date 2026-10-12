"""Korean AI TTS Studio desktop dashboard. CPU work stays off Tk's UI thread."""
import json
import re
import threading
import time
import tkinter as tk
from pathlib import Path
from tempfile import TemporaryDirectory
from tkinter import filedialog, messagebox, ttk

from neural_engine import EMOTIONS, NeuralTTS, parse_emotion
from srt_sync import parse_srt, render


def cue_summary(data):
    if '-->' in data:
        cues = parse_srt(data)
        return len(cues), len({speaker for _, _, speaker, _ in cues}), True
    return (1 if data.strip() else 0), 1 if data.strip() else 0, False


def format_duration(seconds):
    seconds = max(0, int(seconds))
    if seconds >= 3600:
        return f'{seconds // 3600}시간 {(seconds % 3600) // 60}분'
    if seconds >= 60:
        return f'{seconds // 60}분 {seconds % 60}초'
    return f'{seconds}초'


class App:
    def __init__(self, root):
        self.root = root
        self.root.title('KOREAN AI TTS STUDIO v1.4 | Dashboard (CPU)')
        self.root.geometry('1010x790')
        self.root.minsize(780, 650)
        self.engine = NeuralTTS()
        self.language = tk.StringVar(value='KR')
        self.emotion = tk.StringVar(value='기본')
        self.strength = tk.DoubleVar(value=0.7)
        self.ref = tk.StringVar()
        self.voice_map = tk.StringVar()
        self.status = tk.StringVar(value='준비 완료 · 대본을 불러오고 음성 생성을 누르세요.')
        self.stage = tk.StringVar(value='대기 중')
        self.progress_label = tk.StringVar(value='0 / 0 구간 · 0%')
        self.elapsed_label = tk.StringVar(value='경과 0초')
        self.eta_label = tk.StringVar(value='남은 시간 계산 전')
        self.script_label = tk.StringVar(value='대본 0구간 · 0명')
        self.running = False
        self.started = None
        self.completed = 0
        self.total = 0
        self._build()
        self.root.after(1000, self._tick)
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)

    def _build(self):
        style = ttk.Style()
        style.configure('Title.TLabel', font=('Malgun Gothic', 17, 'bold'))
        style.configure('Section.TLabel', font=('Malgun Gothic', 11, 'bold'))
        style.configure('Progress.Horizontal.TProgressbar', thickness=20)
        base = ttk.Frame(self.root, padding=18)
        base.pack(fill='both', expand=True)
        ttk.Label(base, text='KOREAN AI TTS STUDIO', style='Title.TLabel').pack(anchor='w')
        ttk.Label(base, text='3개 언어 · SRT 다중 화자 · CPU 신경망 음성 생성', foreground='#555').pack(anchor='w', pady=(0, 12))

        settings = ttk.LabelFrame(base, text='① 음성 설정', padding=12)
        settings.pack(fill='x', pady=(0, 10))
        r = ttk.Frame(settings); r.pack(fill='x')
        ttk.Label(r, text='언어').pack(side='left')
        ttk.Combobox(r, textvariable=self.language, values=['KR', 'EN', 'JP'], state='readonly', width=7).pack(side='left', padx=(5, 18))
        ttk.Label(r, text='감정').pack(side='left')
        ttk.Combobox(r, textvariable=self.emotion, values=list(EMOTIONS), state='readonly', width=11).pack(side='left', padx=(5, 18))
        ttk.Label(r, text='표현 강도').pack(side='left')
        ttk.Scale(r, from_=0, to=1, variable=self.strength, length=170).pack(side='left', padx=7)
        rr = ttk.Frame(settings); rr.pack(fill='x', pady=(10, 0))
        ttk.Button(rr, text='참조 음성 선택', command=self.pick_ref).pack(side='left')
        ttk.Button(rr, text='화자별 음성 JSON', command=self.pick_voice_map).pack(side='left', padx=8)
        self.reference_label = ttk.Label(rr, text='참조 음성 미선택', foreground='#555')
        self.reference_label.pack(side='left', padx=6)

        editor_box = ttk.LabelFrame(base, text='② 대본 입력 · TXT / SRT', padding=10)
        editor_box.pack(fill='both', expand=True, pady=(0, 10))
        tools = ttk.Frame(editor_box); tools.pack(fill='x', pady=(0, 7))
        ttk.Button(tools, text='파일 불러오기', command=self.load).pack(side='left')
        ttk.Button(tools, text='대본 분석', command=self.analyze).pack(side='left', padx=7)
        ttk.Label(tools, textvariable=self.script_label).pack(side='right')
        text_frame = ttk.Frame(editor_box); text_frame.pack(fill='both', expand=True)
        self.editor = tk.Text(text_frame, font=('Malgun Gothic', 11), wrap='word', height=10, undo=True)
        self.editor.pack(side='left', fill='both', expand=True)
        scroll = ttk.Scrollbar(text_frame, command=self.editor.yview)
        scroll.pack(side='right', fill='y'); self.editor.configure(yscrollcommand=scroll.set)
        self.editor.insert('1.0', '[나레이터] {기쁨} 안녕하세요. AI 음성 생성 테스트입니다.')
        self.editor.bind('<KeyRelease>', lambda _event: self._refresh_summary())
        self._refresh_summary()

        progress_box = ttk.LabelFrame(base, text='③ 생성 진행 현황', padding=12)
        progress_box.pack(fill='x', pady=(0, 10))
        ttk.Label(progress_box, textvariable=self.stage, style='Section.TLabel').pack(anchor='w')
        self.progress = ttk.Progressbar(progress_box, maximum=100, value=0, mode='determinate', style='Progress.Horizontal.TProgressbar')
        self.progress.pack(fill='x', pady=(10, 7))
        line = ttk.Frame(progress_box); line.pack(fill='x')
        ttk.Label(line, textvariable=self.progress_label).pack(side='left')
        ttk.Label(line, textvariable=self.elapsed_label).pack(side='left', padx=20)
        ttk.Label(line, textvariable=self.eta_label).pack(side='right')
        ttk.Label(progress_box, textvariable=self.status, wraplength=900, foreground='#444').pack(anchor='w', pady=(8, 0))

        footer = ttk.Frame(base); footer.pack(fill='x')
        self.btn = ttk.Button(footer, text='▶ WAV 음성 생성 시작', command=self.start)
        self.btn.pack(side='left')
        ttk.Label(footer, text='첫 모델 다운로드 및 CPU 추론 중에는 한 구간이 오래 걸릴 수 있습니다.', foreground='#666').pack(side='left', padx=12)

    def _refresh_summary(self):
        try:
            n, speakers, is_srt = cue_summary(self.editor.get('1.0', 'end').strip())
            self.script_label.set(f'{"SRT" if is_srt else "TXT"} · {n}구간 · {speakers}명')
        except Exception:
            self.script_label.set('SRT 형식을 확인하세요')

    def pick_ref(self):
        p = filedialog.askopenfilename(filetypes=[('Audio', '*.wav *.mp3')])
        if p:
            self.ref.set(p)
            self.reference_label.config(text='참조: ' + Path(p).name)

    def pick_voice_map(self):
        p = filedialog.askopenfilename(filetypes=[('JSON', '*.json')])
        if p:
            self.voice_map.set(p)
            self.reference_label.config(text='화자 설정: ' + Path(p).name)

    def load(self):
        p = filedialog.askopenfilename(filetypes=[('Scripts', '*.txt *.srt')])
        if p:
            try:
                data = Path(p).read_text(encoding='utf-8-sig')
                self.editor.delete('1.0', 'end')
                self.editor.insert('1.0', data)
                self._refresh_summary()
                self.status.set('불러옴: ' + Path(p).name)
            except Exception as e:
                messagebox.showerror('파일 오류', str(e))

    def analyze(self):
        self._refresh_summary()
        messagebox.showinfo('대본 분석', self.script_label.get())

    def start(self):
        if self.running:
            return
        data = self.editor.get('1.0', 'end').strip()
        if not data:
            messagebox.showwarning('대본 필요', '대본을 입력하세요.')
            return
        try:
            total, _, is_srt = cue_summary(data)
            if not total:
                raise ValueError('대본에 생성할 문장이 없습니다.')
        except Exception as e:
            messagebox.showerror('SRT 오류', str(e))
            return
        out = filedialog.asksaveasfilename(defaultextension='.wav', filetypes=[('WAV', '*.wav')])
        if not out:
            return
        self.running = True
        self.started = time.monotonic()
        self.completed = 0
        self.total = total
        self.btn.configure(state='disabled')
        self.progress.configure(value=0)
        self.progress_label.set(f'0 / {total} 구간 · 0%')
        self.eta_label.set('남은 시간 계산 중')
        self.stage.set('모델 준비 및 음성 생성 중')
        self.status.set('첫 구간 생성 중 · 첫 실행에서는 모델 다운로드가 필요할 수 있습니다.')
        args = (data, out, self.language.get(), self.emotion.get(), self.strength.get(), self.ref.get(), self.voice_map.get())
        threading.Thread(target=self.work, args=args, daemon=True).start()

    def _tick(self):
        if self.running and self.started is not None:
            self.elapsed_label.set('경과 ' + format_duration(time.monotonic() - self.started))
            if self.completed:
                elapsed = time.monotonic() - self.started
                remaining = elapsed / self.completed * (self.total - self.completed)
                self.eta_label.set('예상 남은 ' + format_duration(remaining))
        self.root.after(1000, self._tick)

    def _cue_done(self, done, total):
        self.completed = done
        self.total = total
        percent = round(100 * done / total)
        self.progress.configure(value=percent)
        self.progress_label.set(f'{done} / {total} 구간 · {percent}%')
        self.stage.set(f'음성 생성 중 · {done}/{total} 완료')
        self.status.set('구간별 생성 완료 시 진행률이 갱신됩니다. 현재 구간의 세부 진행률은 제공되지 않습니다.')

    def _finish(self, success, message):
        self.running = False
        self.btn.configure(state='normal')
        self.stage.set('완료' if success else '오류 발생')
        self.status.set(message)
        if success:
            self.progress.configure(value=100)
            self.progress_label.set(f'{self.total} / {self.total} 구간 · 100%')
            self.eta_label.set('남은 시간 0초')
        else:
            self.eta_label.set('작업 중단')
            messagebox.showerror('음성 생성 실패', message)

    def work(self, data, out, lang, emotion, strength, reference, voice_map_path):
        try:
            voice_map = {}
            if voice_map_path:
                voice_map = json.loads(Path(voice_map_path).read_text(encoding='utf-8-sig'))
                if not isinstance(voice_map, dict):
                    raise ValueError('화자별 음성 JSON은 객체여야 합니다.')
                for name, path in voice_map.items():
                    if not isinstance(name, str) or not isinstance(path, str) or not Path(path).is_file():
                        raise ValueError('화자별 음성 경로가 유효하지 않습니다: ' + str(name))
            if '-->' in data:
                cues = parse_srt(data)
                with TemporaryDirectory() as temp:
                    files = []
                    for i, (start, end, speaker, line) in enumerate(cues):
                        match = re.match(r'^(KR|EN|JP):(.+)$', speaker, re.I)
                        cue_lang = match.group(1).upper() if match else lang
                        cue_emotion, clean = parse_emotion(line, emotion)
                        path = Path(temp) / f'{i:05d}.wav'
                        voice_ref = voice_map.get(speaker, voice_map.get(match.group(2) if match else speaker, reference or None))
                        self.engine.generate(clean, path, cue_lang, cue_emotion, strength, voice_ref)
                        files.append(path)
                        self.root.after(0, self._cue_done, i + 1, len(cues))
                    self.root.after(0, self.stage.set, '최종 WAV 믹싱 중')
                    warnings = render(cues, files, out, rate=24000, max_speed=1.0, overflow='warn')
                Path(out + '.sync_report.txt').write_text('\n'.join(warnings) if warnings else '싱크 초과 경고 없음', encoding='utf-8')
            else:
                text = re.sub(r'^\s*\[[^]]+\]\s*', '', data)
                cue_emotion, clean = parse_emotion(text, emotion)
                self.engine.generate(clean, out, lang, cue_emotion, strength, voice_map.get('나레이터', reference or None))
                self.root.after(0, self._cue_done, 1, 1)
            self.root.after(0, self._finish, True, '저장 완료: ' + out)
        except Exception as e:
            self.root.after(0, self._finish, False, '오류: ' + str(e))

    def _on_close(self):
        if self.running:
            if not messagebox.askyesno('작업 진행 중', '작업이 진행 중입니다. 종료하면 생성이 중단될 수 있습니다. 종료할까요?'):
                return
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
