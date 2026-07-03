# Release Candidate 아키텍처 (Phase 6)

Phase 5의 데스크톱 아키텍처(`docs/desktop-architecture.md`)를 그대로 유지하며
제품 완성도·데이터 안전성을 더한 것이 Phase 6 RC다. Electron/React/Tauri로
재작성하지 않았고 FastAPI + pywebview + PyInstaller one-dir 구조를 보존했다.

## 계층

```text
desktop/launcher.py          실행·생명주기 (비즈니스 로직 없음)
  ├─ single_instance.py       중복 실행 방지 (lock + PID/health 이중 확인)
  ├─ server_manager.py        동적 포트 + in-process uvicorn 스레드 + graceful shutdown
  └─ pywebview                네이티브 창

app/                          모든 비즈니스 로직 (launcher가 import)
  ├─ main.py                  FastAPI 엔드포인트
  ├─ scorer.py / feedback.py / vocab_analysis.py  Offline Core 채점
  ├─ build_a_sentence_*.py    문장 조립 (15문항 + 결정론 엔진)
  ├─ db.py                    submissions.db (제출/BAS/draft/설정)
  ├─ backup.py                백업·복원 (Phase 6 신규)
  ├─ data_migration.py        legacy 경로 마이그레이션
  ├─ paths.py                 OS 표준 경로 + 리소스 경로 추상화
  └─ version.py               버전 단일 출처
```

## Phase 6에서 추가된 데이터 안전 계층

```text
작성 중 답안:  localStorage (즉시) + drafts 테이블 (800ms 디바운스, 강제종료 대비)
백업:          submissions.db → API 키 제거 → zip (스냅샷 + metadata)
복원:          검증 → 현재 데이터 안전 백업 → 교체 → 레코드 수 확인 → 실패 시 롤백
전체 삭제:     확인 문구 → 자동 안전 백업 → 내용 삭제 (테이블 구조 유지)
업데이트:      CREATE TABLE IF NOT EXISTS (idempotent) → 기존 기록 ID·필드 보존
```

## 생명주기 안전성 (Phase 6 개선)

- graceful shutdown: 신호 핸들러가 서버 종료·lock 해제를 먼저 끝낸 뒤
  `os._exit(0)`으로 즉시 종료 → pywebview 네이티브 스레드와 Py_Finalize 충돌로
  인한 SIGABRT(exit=-6)를 제거. 최초·재실행 두 종료 모두 clean exit(0)을
  smoke test가 assert로 강제(회귀 방지).
- 고아 프로세스: in-process 스레드 구조상 별도 자식 프로세스가 없어 구조적으로
  불가능
- 중복 실행: 두 번째 인스턴스는 서버/DB writer를 만들지 않고 안내 후 종료

## Offline Core 불변식 (API/인터넷 없이 동작)

문제 선택·답안 작성·자동저장·휴리스틱 채점·문법/어휘/구조 분석·결과·기록·
대시보드·PDF·Build a Sentence·백업·복원·설정 — 전부 외부 호출 없이 동작.
Cloud AI(Claude)는 opt-in shadow 전용이며 사용자 점수에 개입하지 않는다.
