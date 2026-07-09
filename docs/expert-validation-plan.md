# Expert Validation Plan

## 목표

실제 교사/전문가 채점 데이터로 Offline Core의 오차와 한계를 측정한다.

## 데이터 필드

- task_type
- prompt
- essay
- official_or_teacher_score
- dimension_scores
- teacher_comments
- corrected_version
- evidence_spans
- rater_id
- adjudication status
- train/validation/test split

## 지원 상태

CSV/JSON import 구조와 sample fixture는 존재한다. 실제 전문가 데이터는 포함하지 않는다.

## 리포트

- MAE
- score band agreement
- dimension agreement
- rater disagreement
- prompt-fit false positives/false negatives
- calibration 후보

## 원칙

가짜 expert data를 만들지 않는다. 전문가 데이터가 없으면 정확도는 unverified로 표기한다.
