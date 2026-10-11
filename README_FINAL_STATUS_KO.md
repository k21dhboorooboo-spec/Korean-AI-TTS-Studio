# KOREAN AI TTS STUDIO v1.1 — 검증 상태

이 패키지는 **Windows 설치형 완제품이 아니라 설치형 EXE 빌드용 소스**입니다.

## 개선
- 신경망 생성 출력을 표준 PCM 16비트 WAV로 저장해 SRT 믹서 입력과 호환되도록 변경
- 화자별 참조 음성 매핑 JSON 추가 (대사에 `[KR:며느리]` 등 사용)
- 별도의 신경망 GUI용 PyInstaller + Inno Setup 빌드 스크립트 추가
- 다국어, SRT, 감정 강도, 기존 단위 테스트 유지

## 사용
1. Python 3.11 64비트 설치 후 `install_neural_windows.bat` 실행
2. `start_neural_windows.bat` 실행
3. 화자별 음성은 `sample_voice_map.json` 형식의 실제 경로를 지정해 등록
4. 설치 파일은 Windows에서 `build_neural_windows.bat` 실행 및 Inno Setup 6 필요

## 한계
- 감정 이름은 신경망의 개별 감정 제어 토큰이 아닙니다. `exaggeration` 강도를 설정하며 특정 감정의 정확한 재현은 보장되지 않습니다.
- 실제 모델 가중치 다운로드/CPU 음성 합성/Windows 빌드/설치/음질은 이 환경에서 검증되지 않았습니다.
- 최초 모델 다운로드는 인터넷이 필요하며 EXE에 모델 가중치는 포함되지 않습니다.
- 음성 복제는 본인 또는 명시적으로 허락받은 샘플에만 사용하세요.
