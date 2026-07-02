# Baseline Audit — 2026-07-02

작업 전 상태 기록. 이 문서는 개선 작업의 기준선이다.

## Git 상태
- 브랜치: `main`, 최근 커밋 `1038457` (Gatekeeper 우회 패치)
- 작업 트리에 미커밋 변경 존재 (main.swift, advanced.py, feedback.py, main.py, vocab_analysis.py, 실행.command 등) — 보존함
- DB: `data/submissions.db` 제출 60건 존재 — 스키마 변경 없이 보존

## 실행 방법
- `실행.command` → `.venv` 자동 생성 → uvicorn + pywebview 네이티브 쉘
- 서버: FastAPI (`app/main.py`), 프론트: `static/` (vanilla JS)
- Python 3.11.15 확인, `.venv` 의존성 정상 (`fastapi, uvicorn, pydantic, httpx, fpdf2, pywebview`)

## Baseline 명령 결과
| 명령 | 결과 |
|---|---|
| `python -m py_compile app/*.py` | 성공 |
| 의존성 import | 성공 (.venv) |
| 테스트 | **테스트 없음** (tests/ 부재) |
| lint/typecheck | 설정 없음 |

## 채점 엔진 구조 (수정 전)
- `app/scorer.py`: 정규식 휴리스틱 채점. `_grammar_risk_count`와 `_grammar_risk_profile`이 **약 40줄 완전 중복**
- `app/advanced.py grammar_error_stats`: 세 번째 중복 구현 (규칙이 서로 불일치)
- `app/ai_mode.py`: 선택적 LLM 보강 (OpenAI/Claude/Gemini) — 패러프레이즈/드릴/샘플 문단만 보강, 점수에는 미반영

## P0 — 채점 변별력 붕괴 (측정 증거)
문법적으로 완벽한 140단어 학술 토론 답안 vs 오류 25개 이상의 저품질 답안:

| | 완벽한 답안 | 오류투성이 답안 |
|---|---|---|
| scorer.py grammar risk | **14 (오탐)** | 13 |
| severe_breakdown 판정 | **True (오판)** | True |
| 최종 밴드 (1–6) | **2.0** | 1.0 |

완벽한 답안이 상한 캡(2.0/5)에 걸려 밴드 2.0을 받음. 원인:

1. `\b(a|an)\s+[aeiou]\w+` — **올바른 "an apple/an essential/an internship"을 전부 관사 오류로 계산**
2. `\b(an)\s+[^aeiou\W]\w+` — 올바른 "an honest/an hour"를 오류로 계산
3. `\b(i|we|they)\s+was\b` — **올바른 "I was"를 시제 오류로 계산** (scorer.py + advanced.py 둘 다)
4. `,\s+(i|we|they|he|she|it)\s+\w+` — "When I was young, I joined..." 같은 **올바른 종속절+주절 구조를 comma splice로 계산**
5. `\bcompared with\b` — 올바른 표현을 전치사 오류로 계산 (advanced.py)
6. `\b(it|this|that)\s+(are|were|have|do|...)` — 관계대명사 "students that have..."를 수일치 오류로 계산 (advanced.py)
7. `[a-zA-Z][.!?][A-Za-z]` — "U.S.", "e.g." 등 약어를 문장부호 오류로 계산
8. `\b(he|she|it)\s+were\b` — 가정법 "if it were"를 오류로 계산
9. `(last year|...)...has` — "Since last year, she has improved"(올바름)를 시제 오류로 계산

`strict_penalty` 1.35 전역 감점은 이 오탐 노이즈를 보정하려던 흔적으로 추정 → 오탐 수정 시 재캘리브레이션 필요.

## P1 — 파이프라인/API 문제
- `app/main.py evaluate()`: prompt-fit 감점이 파생 데이터(시뮬레이터·프로젝션·피드백) 계산 **후에** 적용 → 표시 점수와 파생 수치 불일치
- 60단어 미달 검사가 전체 분석 완료 **후에** 실행 (낭비 + 순서 오류)
- 평가 결과에 엔진/루브릭 버전 미기록 → 재현 불가
- CORS `allow_origins=["*"]` (로컬 앱인데 전체 개방)

## P1 — 프론트엔드
- **문제 지문(prompt) 입력란 부재** → `prompt_text`가 항상 빈 문자열 → prompt_fit 무의미, "평균 적합성" 지표 왜곡
- 대부분의 렌더러가 에세이 원문을 `innerHTML`로 삽입 → **HTML 인젝션** (highlight 프리뷰만 이스케이프)
- 결과 카드 30여 개가 동시 전부 노출 — 정보 위계 부재
- "연습용 예상 점수" 고지 없음. "30점 환산", "Total 범위" 등 공식 점수처럼 오해 소지
- 접근성: reduced-motion 미지원, 아이콘/배지 대비 부족

## 공식 기준 대비
- 2026 개정 TOEFL Writing: Build a Sentence / Write an Email / Writing for an Academic Discussion, 밴드 1–6
- 현재 앱: email + academic_discussion 지원, Build a Sentence 미지원
- `TOEFL_BAND_TABLE`(타 섹션 점수 범위)와 30점 환산은 공식 근거 불명 → 참고용 표기 필요

## 데이터
- 제출 60건 + PDF 리포트 (로컬 전용, 외부 전송 없음 확인)
- API 키: `.env` 로컬 + DB app_settings 저장, 클라이언트 번들 노출 없음 (서버 경유 호출 확인)
