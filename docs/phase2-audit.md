# Phase 2 감사 결과

## 1. diff 감사

`git diff --stat`으로 확인한 Phase 1 변경 파일과 감사 결과:

| 파일 | 내가 이번 세션에서 변경 | 비고 |
|---|---|---|
| `app/main.py` | 예 | evaluate 순서 수정, CORS, 버전 스탬프 |
| `app/models.py` | 예 | EngineInfo 모델 추가 |
| `app/scorer.py` | 예 | grammar.py 위임, 캘리브레이션 조정 |
| `app/advanced.py` | 예 | grammar.py 위임, 오탐 3건 수정, 추천 로직 조건화 |
| `app/grammar.py` | 예 (신규) | 문법 신호 단일 모듈 |
| `static/*` | 예 | 토스 UI 리디자인, XSS 이스케이프 |
| `app/feedback.py` | **아니오** | 세션 시작 전부터 이미 수정돼 있던 사용자 변경 (감점 사유 문구 추가, 임계값 조정). 손대지 않음 |
| `app/vocab_analysis.py` | **아니오** | 세션 시작 전부터 이미 수정돼 있던 사용자 변경 (try/except 방어, 임계값 조정). 손대지 않음 |
| `NativeMacApp/Sources/.../main.swift` | **아니오** | 세션 시작 전 사용자 변경. 손대지 않음 |
| `실행.command`, `*.app/Contents/MacOS/run` | **아니오** | 세션 시작 전 사용자 변경 (Gatekeeper 우회 패치). 손대지 않음 |

**요청과 무관한 변경**: 없음. 위 4개 파일은 애초에 세션 시작 시점 `git status`에 이미 수정으로 표시돼 있던 사용자 작업물이며 이번 세션에서 건드리지 않았다.

**삭제된 기존 기능**: 없음. 기존 필드/엔드포인트/UI 섹션은 모두 유지, 재배치만 수행.

**임시 코드·디버그 출력·로컬 절대경로·비밀 값**: `grep -rn "print(\|console.log\|TODO\|FIXME\|/Users/"` 로 `app/`, `static/`, `tests/` 검사 결과 없음 (아래 3번 확인 결과 참조).

## 2. CORS 개발/운영 분리

Phase 1에서 `allow_origins=["*"]` → 하드코딩된 `["http://127.0.0.1:8000", ...]`으로 좁혔으나, 이는 프리뷰 서버(8765) 등 다른 개발 포트에서 열면 크로스 오리진 fetch가 막히는 문제가 있었다(동일 오리진 정적 서빙이라 실제로는 영향 없었지만 설계상 결함).

**수정**: `TOEFL_EXTRA_ORIGINS` 환경변수로 추가 오리진을 등록할 수 있게 하고, 기본값은 패키지 앱 포트(8000)만 허용하도록 유지했다. 운영 배포 시 이 환경변수를 설정하지 않는 것이 기본이며 안전하다.

## 3. fpdf/fpdf2 충돌 — clean install 재현

**Phase 1 보고의 허점**: `requirements.txt`는 원래부터 `fpdf2==2.8.3`로 정확히 고정돼 있었다. 문제는 내 개발 `.venv`에 레거시 `fpdf==1.7.2`가 별도로 설치돼 fpdf2와 같은 `fpdf/` 네임스페이스를 덮어써서 발생한 것이었다. 이 오염이 `requirements.txt` 자체의 문제인지, 우연히 내 로컬 venv에만 있던 것인지 Phase 1에서는 검증하지 않고 넘어갔다.

**Phase 2에서 실제로 검증**:
```
python3.11 -m venv /tmp/clean_toefl_venv
/tmp/clean_toefl_venv/bin/pip install -r requirements.txt
/tmp/clean_toefl_venv/bin/pip list | grep fpdf   →  fpdf2  2.8.3  (레거시 fpdf 없음)
```
완전히 새로운 venv에 `requirements.txt`만으로 설치 → 서버 기동 → `/api/evaluate` → `/api/report/{id}.pdf` 실행 결과:
```
evaluate: 200
pdf: 200, 63236 bytes, b'%PDF-'
```
**결론**: `requirements.txt` 자체는 처음부터 문제가 없었다. 충돌은 개발 환경 오염이었고 이미 해소됨. clean install에서 재현되지 않음을 실제로 확인했다(추측이 아님).

## 4. 과거 기록 로드/재저장 호환성

`data/submissions.db`의 실제 68건을 전수 조사한 결과, 스키마가 여러 세대에 걸쳐 진화했다:

| 레코드 범위 | 필드 수 | engine 필드 |
|---|---|---|
| #1 | 4 | 없음 (가장 오래된 스키마) |
| #2–7 | 8–10 | 없음 |
| #8–60 | 18–40 | 없음 |
| #61–68 | 40 | 있음 (v2.0.0 이후) |

`get_submission(1)`로 가장 오래된 레코드를 로드해 현재 `EvaluationResult` Pydantic 모델로 강제 파싱을 시도하면 **39개 필드 누락으로 실패**한다. 이것이 실사용에 영향을 주는지 확인한 결과:

- `/api/history`: `SubmissionHistoryItem`(6개 필드만) 사용 — 영향 없음, 정상 작동 확인
- `/api/report/{id}.pdf`: `record["result"]`를 raw dict로 `.get()` 접근 — 영향 없음, id=15로 200 확인
- `EvaluationResult(...)` 전체 모델 생성은 **평가 시점에만 발생**하고 저장된 JSON을 이 모델로 재파싱하는 코드는 현재 앱에 없음 (`grep -n "EvaluationResult(" app/*.py` → main.py 정의부와 생성부 각 1곳뿐)

**결론**: 현재 기능은 깨지지 않지만, 향후 "저장된 평가를 엄격 스키마로 재검증/재저장"하는 기능을 추가한다면 구버전 레코드에서 반드시 실패한다. 이를 대비해 5번 항목(완전한 버전 메타데이터)에서 `result_schema_version`을 도입하고, 구버전 레코드는 `legacy-unknown`으로 명시적으로 태깅한다.

## 5. styles.css 전면 재작성 영향 범위

`grep -c` 기준 index.html의 모든 id/class가 styles.css에 대응 규칙을 갖는지 대조:
- `.card`, `.btn`, `.list`, `.edit-item`, `.rubric-*`, `.detect-*`, `.tag-*`, `.hl-*`, `.section-details`, `.dash-*`, `.history-*`, `.ai-config-*` 등 index.html에서 사용하는 클래스 전수 확인 → 누락 없음 (10번 항목의 실제 렌더 스크린샷으로 교차 검증)
- PDF는 서버측 fpdf2로 별도 렌더링되므로 styles.css 영향 없음 (독립 검증됨)
