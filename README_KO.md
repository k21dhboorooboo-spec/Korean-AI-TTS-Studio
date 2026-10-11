# KOREAN AI TTS STUDIO v0.7 — Windows installer build candidate

**이 ZIP은 설치형 EXE 자체가 아닙니다.** Linux 작업 환경에서 제작된 Windows 설치 프로그램 *빌드용 소스*입니다. Windows 10/11 64비트에서 실제 설치/생성/음성복제 검증을 하지 않았습니다.

## 구현 범위
- 한국어/영어/일본어 MeloTTS CPU 모델 연결, 실제 음성 수는 모델별로 다름
- TXT 및 SRT 불러오기, SRT 시작시각 동기화, 타임코드 겹침/짧은 구간 경고 및 종료 초과 보고서
- 6가지 콘텐츠 모드, 화자별 모델 음성 매핑 및 SQLite 로컬 라이브러리
- 동일 대본/언어/속도/참조음성 SHA256 기반 WAV 캐시
- TXT/SRT 폴더 일괄 생성, 배치 리포트, WAV/MP3(ffmpeg 필요)
- 권한을 확인한 음성 샘플 등록, OpenVoice V2 변환용 연결 코드 (별도 엔진 및 임베딩 필요)
- Windows PyInstaller 빌드 및 Inno Setup 설치파일 제작 스크립트

## Windows에서 빌드하는 순서
1. Python 3.10 (64비트), Git for Windows, Inno Setup 6, FFmpeg(MP3 저장시)를 설치합니다.
2. `install_windows.bat` 실행. MeloTTS 설치 및 첫 모델 다운로드에는 인터넷이 필요합니다.
3. `start_windows.bat`로 개발 모드 실행 확인.
4. `build_windows.bat` 실행. PyInstaller 출력은 `dist/KoreanAITTSStudio/`, Inno Setup 설치파일은 `dist_installer/`에 생성됩니다. Inno Setup의 ISCC.exe를 PATH에 등록해야 자동 빌드됩니다.
5. Windows 실제 기기에서 KR/EN/JP 각각 짧은 문장 생성, SRT 시간 동기화, MP3, 복제 모델 구성, 설치 및 제거를 검증해야 배포 가능합니다.

## 알려진 한계
- MeloTTS 공식 안내는 Windows에서 Docker를 권장합니다. 순수 Windows pip 설치 및 PyInstaller `--collect-all` 빌드는 성공이 보장되지 않습니다.
- OpenVoice V2는 별도 체크포인트, 모델 코드, 화자별 기본 임베딩이 필요합니다. 단순 음성 샘플 등록만으로 복제가 완성되지는 않습니다.
- SRT의 긴 대사는 경고 후 구간을 넘을 수 있습니다. 중첩 대사는 합성되어 출력됩니다. 무손실 타임스트레치가 아니므로 가속 시 음높이가 달라질 수 있습니다.
- 자동 언어 식별, 자동 등장인물 감지, 감정 연기, 고품질 음질 평가, 완전 오프라인 설치 패키지는 아직 제공되지 않습니다.
- 일괄 처리 및 UI 통합 동작은 실제 Windows에서 추가 검증이 필요합니다.
- 음성 복제는 본인 음성 또는 명시적으로 허가받은 음성에 한합니다.

## 확인된 테스트
표준 라이브러리 기반 단위 테스트 9개, Python 구문 검사, ZIP 무결성 검사. 실제 TTS 음질/성능/Windows 설치 검증은 미실시.

참고: https://github.com/myshell-ai/MeloTTS , https://github.com/myshell-ai/OpenVoice , https://pyinstaller.org/
