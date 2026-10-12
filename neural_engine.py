"""Optional neural expressive TTS. No speed/volume fakery.
Chatterbox multilingual uses prompt audio and exaggeration control; model files download separately.
"""
from pathlib import Path
import re
LANGUAGES={'KR':'ko','EN':'en','JP':'ja'}
EMOTIONS={'기본':0.45,'기쁨':0.70,'슬픔':0.65,'분노':0.85,'놀람':0.80,'공포':0.75,'속삭임':0.35,'진지함':0.40,'다정함':0.50,'긴박함':0.75}
TAG=re.compile(r'^\s*\{([^}]+)\}\s*')
def parse_emotion(text,default='기본'):
    m=TAG.match(text)
    if m and m.group(1) in EMOTIONS:return m.group(1),text[m.end():]
    return default,text
def neural_parameters(emotion,strength):
    if emotion not in EMOTIONS:raise ValueError('지원하지 않는 감정')
    strength=max(0,min(1,float(strength)))
    return {'exaggeration':max(0,min(1,0.5+(EMOTIONS[emotion]-0.5)*strength)),'cfg_weight':0.5}
class NeuralTTS:
    def __init__(self):self.models={}
    def generate(self,text,out,language='KR',emotion='기본',strength=0.7,reference=None):
        if language not in LANGUAGES:raise ValueError('지원 언어: KR EN JP')
        if reference and not Path(reference).is_file():raise FileNotFoundError(reference)
        try:
            import torch,torchaudio
            from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        except (ImportError, OSError) as e:
            raise RuntimeError(f'신경망 엔진 로딩 실패 ({type(e).__name__}: {e}). 진단 로그를 확인하세요. 설치된 EXE에는 BAT 설치가 적용되지 않습니다.') from e
        if language not in self.models:
            self.models[language]=ChatterboxMultilingualTTS.from_pretrained(device='cpu')
        model=self.models[language]
        params=neural_parameters(emotion,strength)
        kwargs=dict(language_id=LANGUAGES[language],**params)
        if reference:kwargs['audio_prompt_path']=str(reference)
        audio=model.generate(text,**kwargs)
        out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
        # Canonical PCM 16-bit WAV for the standard-library SRT mixer.
        # Chatterbox may return [channels, samples] float tensors.
        import wave
        pcm=(audio.detach().cpu().float().clamp(-1,1)*32767).round().to(torch.int16)
        if pcm.ndim==1: pcm=pcm.unsqueeze(0)
        if pcm.ndim!=2: raise ValueError('Unexpected neural audio tensor shape')
        if pcm.shape[0]>1: pcm=pcm.float().mean(dim=0,keepdim=True).round().to(torch.int16)
        with wave.open(str(out),'wb') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(int(model.sr))
            wf.writeframes(pcm.contiguous().numpy().tobytes())
        return out
