"""Optional OpenVoice V2 converter. Offline once OpenVoice and checkpoints are installed.
Requires OPENVOICE_ROOT and OPENVOICE_CHECKPOINTS environment variables.
"""
import os,sys
from pathlib import Path

def convert_voice(source_wav,reference_wav,output_wav,language,voice):
    root=Path(os.environ.get('OPENVOICE_ROOT',''))
    checkpoints=Path(os.environ.get('OPENVOICE_CHECKPOINTS',''))
    if not os.environ.get('OPENVOICE_ROOT') or not os.environ.get('OPENVOICE_CHECKPOINTS'):
        raise RuntimeError('참조 음성 변환에는 OpenVoice V2 설치와 OPENVOICE_ROOT / OPENVOICE_CHECKPOINTS 설정이 필요합니다. README 참조.')
    if not (root/'openvoice').exists() or not checkpoints.exists():
        raise RuntimeError('OpenVoice 설치 폴더 또는 체크포인트를 찾을 수 없습니다.')
    if not Path(reference_wav).is_file():raise FileNotFoundError(reference_wav)
    sys.path.insert(0,str(root))
    import torch
    from openvoice import se_extractor
    from openvoice.api import ToneColorConverter
    converter=ToneColorConverter(str(checkpoints/'converter'/'config.json'),device='cpu')
    converter.load_ckpt(str(checkpoints/'converter'/'checkpoint.pth'))
    # Source voice embedding must match the MeloTTS base voice used.
    # Configured explicitly to prevent accidental incorrect voice conversion.
    embed_dir=Path(os.environ.get('OPENVOICE_BASE_EMBEDDINGS',''))
    if not os.environ.get('OPENVOICE_BASE_EMBEDDINGS'):
        raise RuntimeError('OPENVOICE_BASE_EMBEDDINGS에 기본 음성 임베딩 폴더를 지정해야 합니다.')
    candidates=[embed_dir/f'{language.lower()}_{voice.lower()}.pth',embed_dir/f'{language.lower()}.pth']
    embed=next((p for p in candidates if p.is_file()),None)
    if embed is None:raise RuntimeError('기본 음성 임베딩 없음: '+', '.join(map(str,candidates)))
    src_se=torch.load(str(embed),map_location='cpu',weights_only=False)
    tgt_se,_=se_extractor.get_se(str(reference_wav),converter, target_dir=str(Path(output_wav).parent/'ref_segments'),vad=True)
    converter.convert(audio_src_path=str(source_wav),src_se=src_se,tgt_se=tgt_se,output_path=str(output_wav),message='')
    if not Path(output_wav).is_file():raise RuntimeError('음성 변환 파일이 생성되지 않았습니다.')
