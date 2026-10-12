# v1.5 진단 패치 (기존 Chatterbox 엔진)

이번 패치는 고속 ONNX 엔진을 추가한 버전이 아닙니다. 먼저 확인된 엔진 미설치/미인식 문제를 추적하기 위한 수정입니다.

- 음성 생성 전에 Chatterbox, Torch, Torchaudio 라이브러리를 검사합니다.
- 엔진 설치 상태 확인 버튼을 추가합니다.
- 오류의 실제 원인과 Python traceback을 `%LOCALAPPDATA%\KoreanAITTSStudio\logs\tts_errors.log`에 기록합니다.
- GitHub Actions 빌드에서 Chatterbox import 검사를 실행하고 PyInstaller 수집 범위를 확장합니다.

주의: Windows EXE와 모델 다운로드 및 음성 생성은 이 Linux 환경에서 검증되지 않았습니다. 모델 다운로드가 필요한 첫 실행에서는 인터넷이 필요합니다. 모델/메모리/패키징 호환성 문제는 여전히 발생할 수 있습니다. 현재 설치된 v1.2와 별개로 새 설치 파일을 빌드해야 적용됩니다.
