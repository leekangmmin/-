# 업데이트 데이터 보존 검증 (Phase 6)

"구조적으로 데이터가 분리됐다"는 추측이 아니라, 실제 구버전→신버전 업데이트
시나리오를 재현해 사용자 데이터가 보존됨을 검증한다(마스터 스펙 16장).

## 배경

Phase 6에서 `submissions.db`에 `drafts` 테이블이 추가됐다(스키마 변화). 실제
업데이트 상황은 "구버전 앱이 만든 DB를 신버전 앱이 여는 것"이다. 실제 과거
빌드 아티팩트가 없으므로, 구버전(v0.5.0) 스키마를 그대로 모사한 fixture DB를
만들어 검증한다.

## fixture (v0.5.0 스키마)

`drafts` 테이블이 **없는** submissions/app_settings/bas_attempts 3-테이블 DB에:
- 제출 기록 2건 (engine=null → legacy로 표시되어야 함)
- Build a Sentence 시도 1건
- 설정 1건 (ai_provider=local)

## 소스 모드 검증 (`tests/test_update_migration.py`, 5개)

| 검증 | 결과 |
| --- | --- |
| 기존 기록 ID 그대로 보존 (1, 2) + legacy 표시 | PASS |
| 새 `drafts` 테이블이 구버전 DB에 안전 추가, 기존 기록 수 불변 | PASS |
| 설정·BAS 기록 보존 | PASS |
| 새 평가가 ID=3으로 이어짐 (충돌·불연속 없음), 신규는 non-legacy | PASS |
| 업그레이드된 DB 백업 시 legacy 기록 포함 | PASS |

## 패키징 모드 검증 (`scripts/update_migration_test.py`)

실제 `.app`을 구버전 fixture 데이터 위에서 실행:

| 단계 | 결과 |
| --- | --- |
| 1. 구버전 fixture 생성 | — |
| 2. 신버전 앱 기동 → 기존 기록 2건 보존(ID 1,2) + legacy 표시 + drafts 테이블 안전 추가 | OK |
| 3. 새 평가 ID=3 (AUTOINCREMENT 이어짐) | OK |
| 4. 구버전 기록 PDF 생성 (29954 bytes) | OK |
| 5. 재시작 → 구·신 기록 3건 + draft 모두 유지 | OK |

`./scripts/build_macos.sh`의 13단계로 매 빌드마다 자동 실행된다.

## 실패 시 복구

업데이트 마이그레이션은 기존 `app/data_migration.py`의 안전 원칙(원본 미삭제,
백업 우선, 실패 시 원본 유지)을 그대로 따른다. 스키마 추가(`CREATE TABLE IF
NOT EXISTS`)는 기존 데이터를 건드리지 않는 idempotent 연산이므로, 앞선 legacy
경로 마이그레이션과 달리 파괴적 변경이 없다. 만약 업데이트 후 문제가 생기면
사용자는 설정 화면의 백업/복원으로 되돌릴 수 있다(`docs/backup-and-restore.md`).
