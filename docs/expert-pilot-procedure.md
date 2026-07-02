# 전문가 파일럿 데이터 수집 절차 (10~20건)

## 목적과 한계
이 절차는 **import 파이프라인과 비교 파이프라인이 실제 데이터에서 정상 동작하는지
검증**하는 것이 목적이다. 10~20건은 파이프라인 검증용 규모이며, **점수 공식의
정확도나 캘리브레이션을 신뢰할 수 있는 규모가 아니다.** 실제 캘리브레이션(전문가
채점 대비 체계적 편향 보정)을 신뢰하려면 훨씬 더 많은 데이터(문항당 수십 건 이상,
task_type/점수 구간별 고른 분포)가 필요하다.

## 템플릿
- `templates/expert_pilot_template.json` — JSON 형식, 1건 작성 예시 포함
- `templates/expert_pilot_template.csv` — CSV 형식, 1건 작성 예시 포함

두 파일 모두 실제 데이터가 아니라 **채워 넣을 틀**이다. JSON 템플릿의
`_instructions` 필드는 실제 데이터 작성 시 삭제한다.

## 필드별 설명 (한국어)

| 필드 | 설명 |
|---|---|
| `record_id` | 이 채점 레코드의 고유 ID. `pilot-0001-raterA`처럼 "답안번호-채점자" 조합 권장 |
| `response_group_id` | 같은 답안에 여러 채점자가 있을 때 묶는 ID. 비워두면 record_id로 자동 설정 |
| `prompt_id` | 문제(프롬프트)의 고유 ID. 같은 문제의 여러 답안을 묶는 데 사용 (dataset split이 이 값을 기준으로 배정됨) |
| `task_type` | `email` 또는 `academic_discussion` |
| `response_text` | 학생 답안 원문. **개인정보(실명, 학교명 등)는 제거하거나 마스킹 권장** |
| `overall_score` | 채점자가 매긴 총점 |
| `score_scale` | 점수 척도 식별자. 이 프로젝트 기준이면 `toefl-1-6` |
| `dimension_scores` | 차원별 점수 목록 (선택 사항이지만 있으면 캘리브레이션 정밀도가 높아짐) |
| `strengths` / `weaknesses` | 채점자가 관찰한 강점/약점 목록 |
| `evidence_spans` | 점수 근거가 되는 원문 발췌. **`text`가 `response_text`의 `start:end` 위치와 정확히 일치해야 import 시 검증을 통과한다** |
| `corrections` | 문법/표현 교정 목록 |
| `rater.rater_id` | **익명 ID 사용 권장** — 실명 대신 `rater-01`, `rater-02` 형식 (아래 "채점자 익명 ID 방식" 참고) |
| `rater.rater_type` | `expert-teacher`(강사) / `trained-rater`(훈련된 채점자) / `researcher`(연구자) |
| `rater.confidence` | 채점자 본인의 확신도 (0~1, 선택 사항) |
| `rubric_version` | 채점에 사용한 루브릭 버전 (아래 "루브릭 버전 기록 방법" 참고) |
| `adjudication` | 여러 채점자 점수가 크게 다를 때 조정 절차 기록 |
| `provenance` | 출처/라이선스 정보. **`source_type: "expert-rating"`, `is_official: false`로 고정** (ETS 공식 자료가 아닌 이상) |
| `dataset_split` | 비워두면 `prompt_id` 해시로 자동 배정됨 (아래 "split 배정 원칙" 참고) |

## 10~20건 파일럿 절차

1. **문항 선정**: 서로 다른 문제(prompt_id) 5~10개를 고른다. 같은 문제에 2~4개
   답안씩 배정하면 10~20건이 된다.
2. **답안 수집**: 실제 학생 답안(동의 확보) 또는 강사가 직접 작성한 예시 답안.
   `is_human_written`을 정확히 표시한다.
3. **채점**: 최소 1명, 가능하면 2명 이상의 채점자가 독립적으로 채점한다
   (아래 "복수 채점 방법" 참고).
4. **개인정보 마스킹**: 답안에 실명·학교명·이메일 등이 있으면 제거하거나
   `[NAME]`, `[SCHOOL]` 같은 플레이스홀더로 치환한다.
5. **JSON/CSV 작성**: 템플릿을 채운다. `evidence_spans`의 `start`/`end`는
   `response_text`를 기준으로 정확한 문자 offset이어야 한다 (0부터 시작,
   Python 슬라이싱 기준 `response_text[start:end]`).
6. **미리보기(dry-run)**:
   ```bash
   .venv/bin/python scripts/import_expert_data.py --preview path/to/pilot.json
   ```
   `invalid` 행이 0이 될 때까지 수정한다.
7. **실제 import**:
   ```bash
   .venv/bin/python scripts/import_expert_data.py --import path/to/pilot.json
   ```
8. **확인**:
   ```bash
   .venv/bin/python scripts/import_expert_data.py --summary
   ```

## 복수 채점 방법 (같은 답안, 여러 채점자)

같은 답안을 여러 채점자가 평가하려면 **같은 `response_group_id`**, **같은
`response_text`**, 서로 다른 `record_id`와 `rater.rater_id`로 각각 별도
레코드를 작성한다. import 시스템은 이를 자동으로 그룹화해 개별 보존한다
(평균으로 뭉개지 않음, `app/expert_data.py`의 `group_ratings()` 참고).

```python
# 채점자 간 불일치 확인 (프로그램 사용 시)
from app.expert_data import compute_rater_disagreement
result = compute_rater_disagreement("pilot-0001", threshold=1.0)
# result["adjudication_required"] 가 True면 두 점수 차이가 threshold를 넘음
```

## 채점자 익명 ID 방식

- 실명, 이메일, 소속을 `rater_id`에 직접 쓰지 않는다.
- `rater-01`, `rater-02`처럼 순번 기반 익명 ID를 사용하고, 실명-ID 매핑표는
  **이 저장소 밖의 별도 비공개 파일**에 보관한다 (필요시 나중에 채점자별
  경향 분석에 활용 가능하도록 매핑은 유지하되, 데이터 파일 자체에는 포함하지 않는다).
- `qualification` 필드에는 익명을 유지하면서 신뢰도 판단에 필요한 정보만 남긴다
  (예: "TOEFL 강의 경력 5년", 특정 기관명 명시 여부는 상황에 따라 결정).

## 루브릭 버전 기록 방법

- 이 프로젝트의 휴리스틱 채점 기준으로 참고 채점한 경우:
  `app/versions.py`의 `RUBRIC_VERSION` 값을 그대로 기록한다
  (현재 `heuristic-6dim-2.0.0+grammar-2.0.0`).
- 강사 자신의 독자적인 루브릭으로 채점한 경우: 별도 버전 문자열을 부여하고
  (예: `instructor-jiwon-v1`), 가능하면 그 루브릭 내용을 별도 문서로 남긴다.
- 루브릭 버전이 다른 레코드는 캘리브레이션 시 **자동 합산하지 않는다** —
  같은 루브릭 버전끼리만 비교/집계한다.

## dataset split 배정 원칙

- `dataset_split`을 비워두면 `prompt_id`를 해시해 자동으로
  development(40%)/calibration(25%)/validation(20%)/locked_test(15%)에 배정된다
  (`app/expert_data.py`의 `_default_split_for_prompt()`).
- **같은 prompt_id의 모든 답안은 항상 같은 split에 들어간다** — 프롬프트 단위로
  분리해 같은 문제의 답안이 development와 validation에 동시에 섞이는 누출을
  방지한다.
- `locked_test`로 배정된 데이터는 프롬프트/루브릭 튜닝 과정에서 반복 열람하지
  않는다 — 최종 검증에만 제한적으로 사용한다.
- 파일럿 10~20건 규모에서는 4개 split에 고르게 나뉘지 않을 수 있다
  (문항 수가 적으면 특정 split이 비거나 쏠릴 수 있음) — 이는 파일럿 단계의
  정상적인 한계이며, 데이터가 늘어나면 자연히 고르게 분산된다.

## 다음 단계 (데이터가 충분히 쌓인 이후)

- 캘리브레이션 파이프라인 구축 (calibration split 사용, validation/locked_test로 평가)
- `docs/scoring-system.md`의 "캘리브레이션 상태" 섹션을 `uncalibrated`에서
  실제 보정 버전으로 갱신
- 절대 정확도(MAE, quadratic weighted kappa 등) 최초 측정 및 보고
