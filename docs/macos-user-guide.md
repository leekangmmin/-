# macOS 사용자 가이드

## 실행

내부 테스트 빌드는 `.app`, ZIP, DMG 형태로 배포할 수 있다. Developer ID 서명과 notarization이 끝나기 전에는 Gatekeeper 경고가 예상된다.

## 데이터

기록은 `~/Library/Application Support/TOEFL Writing/` 아래에 저장된다. 앱을 삭제해도 사용자 데이터는 남을 수 있다.

## 오프라인 사용

기본 채점, 기록, PDF, Build a Sentence, backup/restore는 API 키 없이 동작해야 한다.

## 공개 배포 전 필수

- Developer ID codesign
- notarization
- artifact security scan
- DMG/ZIP checksum
- release notes
- 알려진 한계 명시
