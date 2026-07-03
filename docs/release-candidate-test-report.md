# macOS Release Candidate 검증 보고서 (Phase 6)

대상: `dist/TOEFL Writing.app` v0.6.0 (`com.leekangmin.toeflwriting`, ad-hoc signed)

## 소스 모드 검증

| 명령 | 종료 코드 | 결과 |
| --- | --- | --- |
| `git diff --check` | 0 | 공백 오류 없음 |
| `py_compile app/*.py desktop/*.py scripts/*.py` | 0 | OK |
| `pytest tests/ -q` | 0 | **237 passed** (Phase 5의 215 + P6 데이터안전 17 + 업데이트 5) |
| `python -m tests.eval_harness` | 0 | 모든 품질 게이트 통과 (오탐 0, 순위역전 0) |

## 패키징 모드 검증 (자동, `build_macos.sh` 14단계)

| 항목 | 결과 |
| --- | --- |
| Info.plist 검증 (version=0.6.0, id, icon=app.icns) | PASS |
| ad-hoc 서명 | 완료 (`Signature=adhoc`) |
| artifact 보안 스캔 | PASS (비밀정보/DB/개발경로 미포함) |
| 최초 실행 → health 200 (offline_core=true, shadow=false, v0.6.0) | OK |
| API 키 없이 평가 → 200 | OK |
| 기록/대시보드/PDF(62512 bytes) | OK |
| graceful shutdown (최초) → exit 0, lock 정리 | OK |
| 재실행 → 이전 기록 유지 | OK |
| graceful shutdown (재실행) → **exit 0** (SIGABRT 수정됨) | OK |
| 업데이트 데이터 보존 (구버전 fixture → 신버전) | PASS |
| release manifest + checksum + zip | 생성됨 |

## 업데이트 데이터 보존 (패키징, `update_migration_test.py`)

구버전(v0.5.0, drafts 테이블 없음) 데이터 위에서 신버전 실행:
- 기존 기록 2건 ID(1,2) 보존 + legacy 표시 ✓
- drafts 테이블 안전 추가 ✓
- 새 평가 ID=3 (충돌 없음) ✓
- 구버전 기록 PDF 생성 ✓
- 재시작 후 3건 + draft 유지 ✓

## 데이터 안전 (소스, `test_data_safety.py` 17개 + `test_update_migration.py` 5개)

draft 저장/로드/삭제, 기록 개별 삭제, 백업 생성/목록/API키 제거/복원 라운드트립/
키 보존/미리보기/손상 zip 거부/경로조작 차단, 전체 삭제 확인문구/안전백업/복구 — 전부 PASS.

## 중복 실행 / 로컬 보안 (수동 재현, Phase 5에서 확인 + P6 재빌드 유지)

- 두 번째 인스턴스 → "이미 실행 중" 다이얼로그 후 종료, 서버 중복 없음
- admin API → 404, shadow → 비활성, 127.0.0.1 전용 bind

## UI 검증 (브라우저 preview 클릭 시뮬레이션)

- 온보딩 3단계 → 시작하기 → 서버 config 저장 확인
- Build a Sentence: 15문항, 난이도 라벨, 정답 제출 → 설명·다음문제·진행("완료 1/15")
- 백업 생성(기록 76건) → 목록 표시 → 복원
- 375px viewport 가로 overflow 0
- 콘솔 에러 0, 실패 요청 0

## DMG (`make_dmg.sh`)

`TOEFL-Writing-macOS-0.6.0.dmg` (30MB) — `.app` + Applications 심볼릭 링크만.
마운트 후 README/log/db/test 파일 유출 없음 확인.

## 수동 검증 필요 (자동화 범위 밖, 미수행)

- **네이티브 pywebview 창 육안 렌더링** — 온보딩 다이얼로그, 백업 UI, 결과
  화면이 실제 창에서 올바르게 그려지는지 사람이 `open dist/TOEFL\ Writing.app`으로
  확인 필요. 스크립트는 서버 API만 검증한다.
- **아이콘 Finder/Dock 표시 육안 확인** — 번들에 app.icns가 있고 Info.plist가
  참조함은 검증했으나, Finder 아이콘 캐시 반영은 사람이 확인 필요
- **VoiceOver 실제 낭독** — semantic HTML/ARIA로 대비했으나 미검증
- **실제 네트워크 차단 상태 육안 실행** — 정적 자산 외부 URL 0건 + API 로컬
  응답으로 실증했으나 "비행기 모드에서 열어봄" 수준은 아님

## 완료 상태

Offline Core validated / UI/UX release polish complete / backup and restore
validated / update migration validated / macOS internal release candidate built /
packaged app smoke validated / app icon integrated / ad-hoc signed / Developer ID
signing pending / notarization pending / external distribution prohibited /
Cloud AI optional / production score path unchanged.
