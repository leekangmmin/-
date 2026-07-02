# 전문가 파일럿 결과 (Phase 4)

## 상태: expert pilot imported — 아니오. expert accuracy pilot measured — 아니오.

## 실제 전문가 데이터 존재 여부
```
.venv/bin/python scripts/import_expert_data.py --summary
Total records: 0
```
**실제 전문가(TOEFL 강사) 채점 데이터는 0건이다.** `data/expert_data.db`는
비어 있다. `tests/expert_data_fixtures/`의 데이터는 전부 `source_type: synthetic`로
표시된 파이프라인 테스트용 합성 데이터이며, 정확도 증거로 사용하지 않는다.

## 이번 세션에 재점검·보강한 것
- `templates/expert_pilot_template.json`, `.csv`: 재검증 완료(JSON 파싱 성공,
  CSV 헤더 확인)
- `docs/expert-pilot-procedure.md`: Phase 2에서 이미 작성된 10~20건 절차,
  익명 rater ID 방식, 복수 채점 저장 방식, rubric 버전 기록법, dataset split
  원칙 문서 — 내용 변경 없음, 유효성만 재확인
- **신규**: `app/pilot_comparison.py` — 전문가/휴리스틱/Claude 3자 비교 계산
  로직(MAE, ±0.5 agreement, 과대/과소평가 카운트, task_type별 분해, 대표
  불일치 사례 탐지, 복수 채점자 합의, 양자화 경계 분석)을 실제 데이터 없이도
  독립적으로 테스트 가능한 순수 함수로 분리 구현(`tests/test_pilot_comparison.py`,
  15개 테스트, 전부 합성 값으로 계산 로직만 검증 — 실제 정확도 주장 아님)
- **신규**: `scripts/run_pilot_comparison.py` — `data/expert_data.db` +
  `data/submissions.db` + `data/shadow_assessments.db`를 텍스트 정확 해시로
  조인해 실제 데이터가 들어오면 즉시 3자 비교를 생성하는 러너. 현재는
  0건이므로 "전문가 데이터 없음 — 가상 데이터로 비교를 만들지 않는다"를
  출력하고 종료함을 실측 확인

## import pipeline 상태
**import pipeline 준비 완료, 실제 데이터 대기.** dry-run/실제 import/rollback/summary
전부 Phase 2~3에서 구현·테스트됐고(`tests/test_expert_data.py`), 이번 세션에는
새로 만든 비교 도구가 "0건일 때 안전하게 0으로 보고하는지"만 추가로 확인했다.

## 다음 단계
1. `docs/expert-pilot-procedure.md` 절차대로 실제 강사 10~20건 확보
2. `scripts/import_expert_data.py --preview` → `--import`
3. `scripts/run_pilot_comparison.py` 재실행 → 최초 3자 비교 수치 확보
4. 결과가 나오면 이 문서를 실제 수치로 갱신하고, "pilot-only / insufficient
   sample" 경고를 함께 유지 (10~20건으로는 정확도 결론을 내리지 않는다)
