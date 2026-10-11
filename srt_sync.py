"""Portable SRT parser and timeline renderer, standard library only (Python 3.10+)."""
import re, wave, math, struct, array, sys
from pathlib import Path
TIME = re.compile(r'^(\d{2,}):(\d{2}):(\d{2})[,.](\d{3})$')

def millis(s):
    m=TIME.fullmatch(s.strip())
    if not m: raise ValueError('잘못된 SRT 시간: '+s)
    h,mi,sec,ms=map(int,m.groups())
    if mi>=60 or sec>=60: raise ValueError('분/초는 60 미만이어야 합니다: '+s)
    return ((h*60+mi)*60+sec)*1000+ms

def parse_srt(data):
    data=data.lstrip('\ufeff').replace('\r\n','\n').replace('\r','\n').strip()
    cues=[]
    for block in re.split(r'\n\s*\n',data):
        lines=block.splitlines()
        if not lines: continue
        idx=next((i for i,line in enumerate(lines) if '-->' in line),None)
        if idx is None: raise ValueError('타임코드 없는 블록: '+block[:40])
        a,b=[v.strip() for v in lines[idx].split('-->',1)]
        start,end=millis(a),millis(b.split()[0])
        if end<=start: raise ValueError('종료시간은 시작시간 이후여야 합니다')
        content=' '.join(v.strip() for v in lines[idx+1:] if v.strip())
        if not content: continue
        speaker='나레이터'
        m=re.match(r'^\s*[\[【]([^\]】]+)[\]】]\s*(.*)$',content)
        if m: speaker,content=m.group(1).strip(),m.group(2).strip()
        if content: cues.append((start,end,speaker,content))
    if not cues: raise ValueError('대사가 없습니다')
    return sorted(cues,key=lambda c:c[0])

def _samples(path,rate):
    with wave.open(str(path),'rb') as w:
        ch,sw,fr,comp=w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getcomptype()
        if comp!='NONE' or sw!=2 or ch not in (1,2):
            raise ValueError('PCM 16-bit mono/stereo WAV만 지원합니다: '+str(path))
        data=w.readframes(w.getnframes())
    a=array.array('h');a.frombytes(data)
    if sys.byteorder!='little': a.byteswap()
    if ch==2: a=array.array('h',((int(a[i])+int(a[i+1]))//2 for i in range(0,len(a),2)))
    if fr!=rate: a=_resample(a,fr,rate)
    return a

def _resample(a,src,dst):
    if not a: return array.array('h')
    n=max(1,round(len(a)*dst/src)); result=array.array('h')
    for i in range(n):
        x=min(len(a)-1,i*src/dst); lo=int(x); hi=min(lo+1,len(a)-1)
        result.append(round(a[lo]*(1-(x-lo))+a[hi]*(x-lo)))
    return result

def render(cues,wav_paths,output,rate=24000,max_speed=1.15,overflow='warn'):
    """Place speech at exact starts. No destructive truncation by default.

    overflow='warn': speech continues after its cue end; warnings report overrun.
    overflow='trim': explicitly truncate to cue end (not recommended).
    Resampling to compress duration also raises pitch; flagged in warnings.
    """
    if len(cues)!=len(wav_paths): raise ValueError('대사/파일 개수 불일치')
    if not 1<=max_speed<=2: raise ValueError('max_speed 범위 오류')
    if overflow not in ('warn','trim'): raise ValueError('overflow 오류')
    items=[];warnings=[];end_sample=math.ceil(max(c[1] for c in cues)*rate/1000)
    for idx,(cue,path) in enumerate(zip(cues,wav_paths),1):
        start,end,speaker,txt=cue
        samples=_samples(path,rate)
        allowed=max(1,round((end-start)*rate/1000))
        if len(samples)>allowed:
            needed=len(samples)/allowed
            if needed<=max_speed:
                samples=_resample(samples,round(rate*needed),rate)
                warnings.append(f'{idx}번 [{speaker}]: {needed:.2f}배 속도 압축(음높이 변동 가능)')
            if len(samples)>allowed:
                warnings.append(f'{idx}번 [{speaker}]: 종료시각 초과 {round((len(samples)-allowed)*1000/rate)}ms / {txt[:32]}')
                if overflow=='trim': samples=samples[:allowed]
        offset=round(start*rate/1000)
        end_sample=max(end_sample,offset+len(samples))
        items.append((offset,samples))
    # bounded output length; stream blocks rather than allocate full-duration buffer
    with wave.open(str(output),'wb') as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate)
        for base in range(0,end_sample,8192):
            block=[0]*min(8192,end_sample-base)
            for offset,samples in items:
                left=max(base,offset);right=min(base+len(block),offset+len(samples))
                for pos in range(left,right): block[pos-base]+=samples[pos-offset]
            pcm=array.array('h',(max(-32768,min(32767,x)) for x in block))
            if sys.byteorder!='little': pcm.byteswap()
            out.writeframesraw(pcm.tobytes())
    return warnings
