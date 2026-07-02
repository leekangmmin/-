# 전문가 데이터 import (Phase 2)

## 현재 상태
**실제 전문가(TOEFL 강사) 채점 데이터는 아직 없다.** 이 문서와 코드는 데이터가
들어왔을 때 즉시 사용할 수 있는 **구조**를 설명한다. `tests/expert_data_fixtures/`의
모든 데이터는 파이프라인 테스트용 합성(synthetic) 데이터이며, provenance에
`source_type: synthetic`, `intended_usage: ui-demo`로 명시돼 있다. 이 합성 데이터를
채점 정확도의 증거로 사용하지 않는다.

## 스키마
`app/expert_models.py`:
- `DataSourceRecord` — 모든 데이터의 출처/라이선스/신뢰 등급 (7~8장 요구사항)
- `ExpertRatedResponse` — 답안 1건 + 채점자 1인의 평가 (9장 요구사항 전체 필드 포함:
  evidence_spans, corrections, rater 정보, adjudication, dataset_split 등)

## 저장·중복탐지·분리 (`app/expert_data.py`)
- **저장**: `data/expert_data.db` (SQLite, 앱 DB와 분리)
- **중복 탐지**: `(정확 해시, rater_id)` + `(정규화 해시, rater_id)` 조합.
  같은 텍스트를 **다른 채점자**가 평가하는 것은 정상(multi-rater)이므로 중복이
  아니다 — 같은 채점자가 같은 텍스트를 다시 제출한 경우만 중복 처리한다.
  (Phase 2 개발 중 이 구분을 놓쳐 multi-rater 케이스를 오탐하는 버그를 발견하고 수정함.)
- **dataset split**: `prompt_id`를 해시해 development(40%)/calibration(25%)/
  validation(20%)/locked_test(15%)에 결정론적으로 배정한다. 같은 문제의 답안은
  항상 같은 split에 들어가 누출을 방지한다.
- **multi-rater**: 평균으로 뭉개지 않고 개별 레코드로 전부 보존한다.
  `group_ratings(response_group_id)`로 조회.
- **adjudication**: `compute_rater_disagreement()`가 채점자 간 최대 점수 차이를
  계산하고, 임계값을 넘으면 `adjudication_required=True`로 표시한다 (자동 확정하지 않음).
- **rollback**: `rollback_import(import_id)`로 특정 import 전체를 취소할 수 있다.
  원본 파일은 절대 수정하지 않는다 (import는 읽기 전용).

## Import 방법

### CLI (실사용)
```bash
.venv/bin/python scripts/import_expert_data.py --preview path/to/data.json   # dry-run
.venv/bin/python scripts/import_expert_data.py --import path/to/data.json    # 실제 import
.venv/bin/python scripts/import_expert_data.py --history                     # import 이력
.venv/bin/python scripts/import_expert_data.py --rollback <import_id>        # 취소
.venv/bin/python scripts/import_expert_data.py --summary                     # split 현황
```

### JSON 형식
최상위가 배열이거나 `{"records": [...]}` 형태. 필드는 `ExpertRatedResponse` 스키마.
예시: `tests/expert_data_fixtures/sample_valid.json`

### CSV 형식
평면 컬럼 + 중첩 필드(`rater`, `provenance`, `evidence_spans` 등)는 셀에 JSON 문자열.
`strengths`/`weaknesses`는 `|`로 구분. 예시: `tests/expert_data_fixtures/sample_valid.csv`

### API (관리자 전용, 기본 비활성화, 읽기 전용)
`GET /api/expert-data/summary` — CORS는 접근 통제가 아니므로, 다음 두 가지를
모두 요구한다: (1) `TOEFL_ADMIN_API_ENABLED=1` 환경변수(기본값은 비활성화이며,
꺼져 있으면 엔드포인트가 아예 없는 것처럼 404를 반환), (2) `127.0.0.1`에서의
접근(`request.client.host` 기준 — `X-Forwarded-For` 같은 클라이언트가 조작
가능한 헤더는 신뢰하지 않는다). 일반 사용자 화면에는 노출하지 않는다.
응답은 집계 수치만 포함하며 답안 원문·개인정보는 포함하지 않는다
(`tests/test_admin_api_security.py`로 회귀 검증). 실제 데이터 업로드는 아직
HTTP 엔드포인트로 제공하지 않는다 — 쓰기 가능한 업로드 엔드포인트를 인증
시스템 없이 여는 것은 위험하므로, 실사용 import는 로컬 CLI로만 수행하도록
설계했다.

## 아직 구현하지 않은 것 (다음 단계)
- 캘리브레이션 파이프라인 자체(`calibration` split 데이터를 실제로 사용해
  `app/scorer.py` 점수를 보정하는 로직) — 전문가 데이터가 없어 아직 만들 수 없다.
- import preview/rollback을 위한 웹 UI (현재는 CLI + 읽기 전용 API만 존재).
- 패러프레이즈/유사 답안 임베딩 유사도 검사 (현재는 정확 해시 + 정규화 해시만).
