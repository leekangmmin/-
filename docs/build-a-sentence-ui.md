# Build a Sentence — 사용자 UI 연결 (Phase 5)

Phase 2에서 만든 결정론적 엔진(`app/build_a_sentence_engine.py`,
`docs/build-a-sentence.md` 참고)을 실제 사용자가 쓸 수 있는 화면에
연결했다. API/인터넷 없이 완전히 동작하는 Offline Core 기능이다.

## 문항 뱅크 (`app/build_a_sentence_items.py`)

Phase 2까지는 `tests/build_a_sentence_fixtures.py`의 문항 3개가 엔진 단위
테스트 전용으로만 존재했다. Phase 5에서 실제 UI에 노출할 프로덕션 문항
뱅크를 새로 만들었다 — **자체 제작 문항 8개**, 전부
`provenance.source_type="synthetic"`, `is_official=False`로 명시했다.

| item_id | 조각 수 | 문법 포인트 |
| --- | --- | --- |
| bas-001 | 4 | 기본 어순 + 부사구 전치 허용 |
| bas-002 | 4 | 부정문 + 축약형 허용 |
| bas-003 | 4 | 고유명사 대소문자 구분(case_sensitive) |
| bas-004 | 4 | 양보 접속사(although) |
| bas-005 | 5 | that절 |
| bas-006 | 5 | neither...nor |
| bas-007 | 5 | 분사구문 + 쉼표(구두점 무시 정책으로 조립 UI와 호환) |
| bas-008 | 4 | the more...the better 비교 구문 |

## API (`app/main.py`, `app/models.py`)

| 엔드포인트 | 설명 |
| --- | --- |
| `GET /api/build-a-sentence/items` | 문항 목록(정답 노출 없음, `item_id`+`fragment_count`만) |
| `GET /api/build-a-sentence/items/{item_id}` | 조각을 **셔플**해서 반환(순서 자체가 힌트가 되지 않도록) — `primary_answer` 필드 없음 |
| `POST /api/build-a-sentence/items/{item_id}/submit` | 제출 채점. `correct_answer`는 **오답일 때만** 채워짐(정답이면 이미 아는 정보이므로 생략) |

채점은 항상 `app/build_a_sentence_engine.py`의 결정론적 로직만 쓴다 — AI를
호출하지 않는다.

## 기록 (`app/db.py`의 `bas_attempts` 테이블)

```sql
CREATE TABLE bas_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    item_id TEXT NOT NULL,
    item_version TEXT NOT NULL,
    rubric_version TEXT NOT NULL,
    engine_version TEXT NOT NULL,
    is_correct INTEGER NOT NULL,
    match_type TEXT NOT NULL,
    time_spent_ms INTEGER,
    attempt_number INTEGER NOT NULL
)
```

마스터 스펙 16장이 요구하는 필드(item ID, item version, provenance,
attempts, 정답 여부, 사용 시간, 적용 정책 버전)를 커버한다. 제출한 문장
원문은 저장하지 않는다(불필요한 개인 데이터 최소화 원칙).

## UI (`static/index.html`, `static/app.js`, `static/styles.css`)

### 최소 기능 구현 상태

| 요구사항 | 구현 |
| --- | --- |
| 문제 목록 | `<select id="basItemSelect">` |
| 문제 시작 | `basStartBtn` → 조각 셔플 GET, pool 초기화 |
| 조각 표시 | `#basFragmentPool`의 버튼들 |
| 클릭/탭으로 배열 | 조각 클릭 → 답안 목록 맨 뒤에 추가 |
| 키보드 사용 가능 | 모든 조각/버튼이 `<button>` 요소라 Tab+Enter/Space로 조작 가능(별도 키보드 단축키 라이브러리 불필요) |
| 모바일 터치 가능 | 클릭 기반이라 터치 이벤트도 네이티브로 동작(드래그 앤 드롭에 의존하지 않음) |
| 위/아래 이동 버튼 | `▲`/`▼` 아이콘 버튼, 첫/끝 항목에서 자동 비활성화 |
| 제거 버튼 | `✕` — 조각을 pool로 되돌림 |
| 직접 입력 fallback | `<details>` 안의 `<textarea id="basDirectInput">` — 조립 UI 없이 전체 문장을 타이핑해도 채점 가능 |
| 제출 | `basSubmitBtn` → direct input이 있으면 그것을, 없으면 조립된 조각을 공백으로 join해서 제출 |
| 정답/오답 판정 표시 | `.bas-feedback.correct` / `.incorrect` 클래스로 시각 구분 |
| 오답 설명 | feedback 텍스트 + `correct_answer` 노출 |
| 다시 시도 | `basResetBtn` → 같은 문항 재시작(조각 재셔플) |
| 결과 기록 | 매 제출마다 서버가 `bas_attempts`에 저장, `attempt_number` 표시 |

### 접근성 설계 의도

마스터 스펙 16장이 "drag-and-drop만 제공하지 마라"고 명시했다 — 이 구현은
애초에 drag-and-drop을 전혀 쓰지 않고 클릭/탭 + 이동 버튼만으로 전체
플로우를 완성했으므로, 별도의 "대안 제공"이 아니라 기본 상호작용 자체가
접근성을 만족한다. 직접 입력 fallback까지 더해 총 두 가지 입력 경로가
있다.

### "공식 문제 아님" 표시

```html
<p class="status-highlight">자체 제작 연습 문제 · ETS 공식 문항이 아닙니다</p>
```

섹션 헤더 바로 아래 항상 표시된다.

## 검증

- `tests/test_build_a_sentence_api.py`(8개, 신규): 목록/상세/제출/404/시도
  횟수 증가/attempts 기록 확인
- `tests/test_build_a_sentence.py`(기존, 엔진 단위 테스트): 3개 fixture
  문항 기준 정규화/정답 판정 로직 검증
- 브라우저 preview에서 실제 클릭 시뮬레이션으로 end-to-end 확인:
  조각 조립 → 정답 제출 → "정답과 정확히 일치합니다" → 재시도 → 직접 입력
  오답 → "정답 예시: ..." 노출까지 전체 플로우 실증(이 세션의 preview 도구
  기록 참고)
- 패키징된 `.app`에서는 API 레벨(목록/상세 GET)만 재확인했다 — 전체
  클릭-투-제출 플로우를 패키징 앱의 실제 네이티브 창에서 재현하지는
  않았다(수동 검증 필요 항목, `docs/internal-alpha-test-report.md` 참고).
