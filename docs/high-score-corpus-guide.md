# 고득점 코퍼스 로컬 분석 가이드

이 기능은 고득점 답안의 문장 자체가 아니라 구조적 경향만 학습 도구에 반영한다. 원문은 `private_corpus/` 아래에 두며 Git에 포함하지 않는다.

```bash
.venv/bin/python scripts/analyze_high_score_corpus.py \
  --input private_corpus/high_score_answers \
  --out private_corpus/processed/safe-report.json --safe-summary

.venv/bin/python scripts/evaluate_against_high_score_corpus.py \
  --input private_corpus/high_score_answers
```

지원 형식은 TXT, Markdown, CSV, PDF다. PDF는 로컬 `pdftotext`가 필요하다. CSV는 `answer_text` 또는 `essay_text`, 선택적으로 `task_type`, `score`, `source_type`, `permission_status` 열을 사용한다. 파일이 없으면 도구는 오류 없이 건너뛴다.

안전 요약에는 표본 수, 유형별 평균 분량, 문장·문단 수, 추상적 글쓰기 동작의 감지율만 포함된다. 답안, 프롬프트, 학생 이름과 원문 발췌는 출력하지 않는다.
