# v1.7 Windows SQLite 테스트 오류 수정

- `VoiceLibrary.all()`에서 SQLite 커서를 명시적으로 닫도록 변경했습니다.
- 테스트 임시 폴더 정리 시 가비지 수집 및 Windows의 일시적인 파일 잠금에 대한 재시도를 추가했습니다.
- 기존 v1.6 패키징 메타데이터 수정 사항은 유지했습니다.
- 로컬 Linux unittest 통과 여부는 별도 확인하며, GitHub Actions Windows 빌드와 실제 음성 생성은 아직 미검증입니다.

GitHub Desktop Summary:
`Fix Windows SQLite test cleanup and retain metadata fixes`
