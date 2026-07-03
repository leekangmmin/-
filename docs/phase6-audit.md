# Phase 6 감사 — Release Candidate 최종 마감 (요약)

## 시작 상태

```text
브랜치: main
직전 커밋: a2b8040 docs(phase5) (Phase 3~5 커밋 16개 확인)
원격: origin/main 대비 로컬 앞섬 (자동 push 안 함)
```

보호한 사용자 미커밋 파일(Phase 6에서 미변경, 커밋 제외):
`app/feedback.py`, `app/vocab_analysis.py`, `실행.command`,
`토플첨삭기 by이강민.app/Contents/MacOS/run`, `.vscode/launch.json`,
`NativeMacApp/.build/**`.

기존 수동 wrapper `.app`(SwiftUI+포트8000 고정)과 Phase 5/6 공식 빌드
(`dist/TOEFL Writing.app`, pywebview one-dir)는 bundle identifier·아키텍처가
달라 공존. 기존 것을 삭제하지 않음.

## 완료 게이트 (마스터 스펙 32장) 판정

| 영역 | 상태 |
| --- | --- |
| **Core** — API/인터넷 없이 실행, 기본 채점, 기록, PDF, Build a Sentence, draft 복구 | ✅ 전부 검증 |
| **Data** — OS 표준 경로, first run, update migration, 백업 UI, 복원 UI, rollback, legacy 데이터, 업데이트 후 보존 | ✅ 전부 검증 |
| **UI** — 온보딩, 홈, 에디터, 로딩, 결과, 기록, 대시보드, Build a Sentence, 설정, 백업, 복원, 오류상태 | ✅ 제품 수준 완성 |
| **Accessibility** — 키보드 코어플로우, focus, contrast, reduced motion, dialog focus | ✅ (VoiceOver 실낭독 미검증) |
| **Desktop** — .app, icon, native window, dynamic port, graceful shutdown, 중복실행, no orphan, restart persistence | ✅ (창 육안 렌더링 수동검증 대기) |
| **Security** — no API key/.env/DB/expert/answer, localhost-only, admin/shadow disabled, Offline Core 외부요청 0 | ✅ 자동 스캔 PASS |
| **Build** — clean build, full tests, package smoke, update smoke, backup/restore smoke, artifact scan, manifest, checksum | ✅ 14단계 파이프라인 |
| **배포 상태** | internal RC / ad-hoc signed / notarization pending / external distribution prohibited |

## 33장 "완료로 보면 안 되는 상태" 점검 — 모두 회피

- UI만 바꾸고 흐름 미검증 ✗ (preview 클릭 시뮬레이션으로 실검증)
- 백업만 있고 복원 안 됨 ✗ (라운드트립 테스트 PASS)
- 복원 실패 시 데이터 손상 ✗ (안전 백업 + 자동 롤백)
- 업데이트를 추측으로 대체 ✗ (fixture 재현 + 패키징 앱 실행 검증)
- 아이콘 파일만 만들고 미적용 ✗ (Info.plist 검증 + 번들 내 확인)
- 개발서버만 테스트 ✗ (패키징 앱 smoke + update 테스트)
- API 없을 때 오류 배너 ✗ (Offline Core = 정상 모드 문구)
- 종료 후 프로세스 잔존 ✗ (exit 0 assert)
- 중복 실행 시 서버 2개 ✗ (single instance)
- 외부 CDN 요청 ✗ (정적 자산 외부 URL 0)
- 빌드에 .env/DB/답안 ✗ (보안 스캔 PASS)
- 미서명인데 배포가능 주장 ✗ (external distribution prohibited 명시)
- 215 테스트 감소 ✗ (215 → 237 증가)
- 사용자 미커밋 파일 커밋 포함 ✗ (제외 확인)
- 실제 Claude 품질 검증 주장 ✗ (Phase 6 범위 밖 명시)

## 최종 검증 명령/결과

| 명령 | 종료코드 | 결과 |
| --- | --- | --- |
| `git diff --check` | 0 | 공백오류 없음 |
| `pytest tests/ -q` | 0 | 237 passed |
| `python -m tests.eval_harness` | 0 | 품질 게이트 통과 |
| `./scripts/build_macos.sh` | 0 | 14단계 전부 통과, RC .app 생성 |
| `./scripts/make_dmg.sh` | 0 | DMG 생성, 유출 없음 |
| `./scripts/sign_and_notarize.sh` | 0 | [SKIP] (인증서 없음, 정상) |

## 주요 변경 파일

| 파일 | 목적 |
| --- | --- |
| `app/backup.py` (신규) | 백업·복원 (키 제거, 롤백, 경로차단) |
| `app/db.py` | drafts 테이블, draft/삭제/카운트/전체삭제 함수 |
| `app/build_a_sentence_items.py` | 문항 8→15개, 난이도/태그/설명 |
| `app/build_a_sentence_models.py` | difficulty/grammar_tag/explanation 필드 |
| `app/main.py` | 온보딩/draft/백업/복원/삭제 API, BAS 응답 확장 |
| `app/models.py` | draft/backup/삭제 요청 스키마, BAS 상세 확장 |
| `app/version.py` | 0.5.0 → 0.6.0 |
| `desktop/launcher.py` | 신호 핸들러 os._exit(0) (SIGABRT 수정) |
| `static/index.html` | 온보딩 다이얼로그, 백업 관리 섹션, BAS 진행/설명/다음 |
| `static/app.js` | 온보딩/draft서버동기화/백업복원/삭제/로딩단계/기록버튼/BAS진행 |
| `static/styles.css` | 온보딩/백업/삭제/BAS설명 컴포넌트 스타일 |
| `packaging/toefl-writing-macos.spec` | 아이콘 연결 |
| `packaging/resources/` (신규) | app.icns, iconset, 마스터 PNG |
| `scripts/` (신규 6개) | generate_app_icon, scan_artifact_security, make_release_manifest, verify_info_plist, update_migration_test, sign_and_notarize, make_dmg |
| `tests/` (신규 2개) | test_data_safety(17), test_update_migration(5) |

## 현재 한계

- 실제 Claude 실호출 미검증 (Phase 6 범위 밖)
- 전문가 정확도 검증 미수행
- Apple Developer 인증서 없음 → codesign/notarization pending, 외부 배포 금지
- Windows 미검증
- 로컬 AI Provider 미구현
- 네이티브 창 육안 렌더링·VoiceOver 실낭독은 수동 검증 대기
