# Offline Core 모드 (Phase 5)

## 원칙

Offline Core는 실패 모드가 아니라 하나의 정상 제품 모드다. API 키가 없거나
인터넷이 끊긴 상태에서 앱이 "제한된" 것처럼 보이면 안 된다.

## API 없이 실제로 검증된 기능

| 기능 | 검증 방식 |
| --- | --- |
| 앱 실행 (API 키 없음) | `scripts/packaged_app_smoke_test.py` — 패키징된 `.app`을 API 키 없이 실행 |
| 문제 선택 / 답안 작성 | `static/index.html` textarea, 자동저장(localStorage) — API 불필요 |
| 60단어 이상 답안 제출 | `POST /api/evaluate` (essay_text 필수) |
| 휴리스틱 평가 / 문법 / 어휘 / 구조 분석 | `app/scorer.py`, `app/vocab_analysis.py` — 순수 로컬 로직, 외부 호출 없음 |
| score breakdown / 예상 점수 | `EvaluateResponse.result` |
| 결과 저장 / history / dashboard | SQLite (`app/db.py`), API 불필요 |
| PDF | `GET /api/report/{id}.pdf` — 로컬 fpdf2 + macOS 시스템 폰트, 외부 호출 없음 |
| 앱 재시작 후 기록 유지 | smoke test 2단계(최초 실행 → 종료 → 재실행)에서 실증 |
| Build a Sentence | `app/build_a_sentence_engine.py` 결정론적 채점, API 불필요 |

`GET /api/health`의 `offline_core_available: true`는 위 기능들이 API 키
유무와 무관하게 항상 사용 가능함을 나타내는 상수다(현재 조건부 비활성화
로직이 없다 — Offline Core는 항상 켜져 있다).

## UI 표시 원칙

"앱 상태 및 분석 모드" 카드(`static/index.html`)는 다음 정책을 표시한다:

```text
클라우드 AI가 꺼져 있으면 내장 기준 점수를 사용합니다.
직접 켜면 검증된 2026 루브릭 AI 과제 점수를 사용하고,
실패 시 내장 점수로 돌아갑니다.
```

그리고 "기본 분석 모드"를 문법/구조/어휘 기반의 정상적인 채점 방식으로
설명한다 — "성능이 크게 떨어졌습니다", "API 키가 없어서 오류가 발생했습니다"
같은 결핍 프레이밍은 어디에도 쓰지 않는다. `static/app.js`의
`fetchAppStatus()`가 `/api/health`를 읽어 `shadow_enabled` 상태를 "AI 심층
분석(Claude): 활성/비활성"으로만 표시하고, 비활성 상태를 오류로 표시하지
않는다.

## 인터넷 차단 상태에서의 UI

Phase 5 이전에는 `static/index.html`이 Pretendard 폰트를 jsdelivr CDN에서
불러왔다(`<link rel="stylesheet" href="https://cdn.jsdelivr.net/...">`).
이를 제거하고 시스템 폰트 우선 fallback으로 교체했다(`static/styles.css`의
`font-family` 스택). `static/index.html`, `static/styles.css`,
`static/app.js` 전체에 `http://`/`https://` 참조가 없음을 확인했다:

```bash
grep -n "cdn\.\|googleapis\|fonts\.google\|http://\|https://" static/index.html static/styles.css
# (결과 없음)
```

패키징된 `.app`도 동일한 로컬 `static/` 파일만 서빙하므로 인터넷 차단 상태의
동작은 소스 모드와 동일하다.

## 검증하지 않은 것 (정직한 한계)

- **실제 Wi-Fi/네트워크 인터페이스를 물리적으로 차단한 상태**에서 macOS
  `.app`을 육안으로 실행 확인하지는 않았다 — 대신 (1) 정적 자산에 외부 URL
  참조가 없음을 코드 감사로 확인했고, (2) 패키징된 서버가 로컬 호출만으로
  모든 API 엔드포인트를 200으로 응답함을 실증했다. 이 두 증거를 결합하면
  네트워크 차단 여부가 결과에 영향을 줄 수 없다는 결론이 나오지만, "비행기
  모드에서 실제로 열어봤다"는 수준의 육안 검증은 아니다.
