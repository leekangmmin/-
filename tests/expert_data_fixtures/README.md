# 전문가 데이터 예시 fixture — 합성 데이터 (SYNTHETIC EXAMPLE)

이 디렉터리의 JSON/CSV 파일은 **실제 전문가(TOEFL 강사) 채점 데이터가 아니다.**
`ExpertRatedResponse` 스키마와 import 파이프라인(JSON/CSV 파싱, 검증, 중복 탐지,
dataset split, 다중 채점자, adjudication)을 테스트하기 위해 이 프로젝트를 위해
직접 작성한 합성 데이터다.

- `provenance.source_type = "synthetic"`, `intended_usage = "ui-demo"`로 명시
- 실제 채점 정확도의 증거로 사용하지 말 것
- 실제 전문가 데이터가 들어오면 이 디렉터리가 아니라 별도 위치(예: `data/expert/`,
  .gitignore 대상)에 저장하고, provenance를 `expert-rating`으로 정확히 기록할 것
