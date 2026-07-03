# 백업과 복원 (Phase 6)

사용자 데이터를 안전하게 보관하고 되돌릴 수 있는 제품 기능. 구현: `app/backup.py`,
API는 `app/main.py`, UI는 `static/index.html`의 "백업 및 데이터 관리" 섹션.

## 백업 대상

사용자 기록이 모두 담긴 `submissions.db` 하나를 백업한다(이 DB에 제출 기록,
Build a Sentence 기록, 작성 중 답안(draft), 사용자 설정이 전부 있다).

포함:
- 답안 제출 기록 (submissions)
- Build a Sentence 시도 기록 (bas_attempts)
- 작성 중 답안 (drafts)
- 사용자 설정 (app_settings)

**제외**:
- `shadow_assessments.db`, `expert_data.db` — 연구·개발용 데이터
- **API 키** — 백업 파일이 다른 기기·사람에게 전달될 수 있으므로, 백업 zip을
  만들 때 `app_settings`의 `openai_api_key`/`anthropic_api_key`/`gemini_api_key`를
  제거한 사본을 담는다. `DELETE` 후 `VACUUM`으로 freed page의 키 바이트까지
  물리적으로 지운다(테스트 `test_backup_strips_api_keys`가 zip 안 DB 바이트에
  키 문자열이 없음을 검증).

## 백업 파일 형식

`~/Library/Application Support/TOEFL Writing/backups/toefl-writing-backup-<날짜>.zip`

zip 내부:
- `submissions.db` — `sqlite3.Connection.backup()` API로 만든 일관된 스냅샷
  (raw 파일 복사가 아니라 WAL/락 안전한 스냅샷), API 키 제거본
- `metadata.json` — 백업 포맷 버전, 앱 버전, DB 스키마 버전, 생성 시각,
  레코드 수, 포함/제외 목록

## 복원 안전 절차 (`restore_backup`)

1. **구조·스키마 검증**: zip에 `metadata.json`/`submissions.db`가 있는지,
   `db_schema_version`이 현재 앱과 일치하는지 확인. 손상된 zip이나 스키마
   불일치는 `RestoreError`로 거부하고 **기존 데이터는 건드리지 않는다**.
2. **무결성 검증**: 스냅샷 DB에 `PRAGMA integrity_check`와 필수 테이블
   (submissions/app_settings/bas_attempts/drafts) 존재 확인.
3. **현재 데이터 자동 안전 백업**: 교체 전에 현재 DB를 `pre-restore-safety-<날짜>.db`로
   스냅샷 → 복원 실패 시 롤백 지점.
4. **교체 + 레코드 수 검증**: 스냅샷을 실제 DB에 덮어쓴 뒤 레코드 수가
   백업 metadata와 일치하는지 확인. 불일치·예외 시 안전 백업에서 **자동 롤백**.
5. **현재 기기 API 키 보존**: 백업에는 키가 제거돼 있으므로, 복원 전에 현재
   기기의 키를 읽어뒀다가 복원 후 다시 넣는다 — 복원해도 이 기기의 AI 연결이
   끊기지 않는다(테스트 `test_restore_preserves_current_api_key`).

## 경로 조작 방지

`_resolve_backup_path`는 `Path(filename).name`으로 파일명만 추출해 backups_dir
안의 파일만 허용한다 — `../../etc/passwd` 같은 경로 탈출을 차단한다(테스트
`test_restore_path_traversal_blocked`).

## 전체 데이터 삭제

`POST /api/data/delete-all`은 확인 문구 "모두 삭제"를 요구한다(불일치 시 400).
삭제 **직전에 자동 백업**을 만들어 실수로 지워도 되돌릴 수 있게 하고
(`safety_backup` 반환), 테이블 구조는 유지한 채 내용만 비운다 → DB 재생성
없이 앱이 계속 정상 동작한다(테스트 `test_delete_all_wipes_and_creates_safety_backup`,
`test_delete_all_recoverable_from_safety_backup`).

개별 기록 삭제는 `DELETE /api/history/{id}` — 다른 기록에 영향 없이 1건만 제거.

## 작성 중 답안(draft) 서버측 보존

localStorage와 별개로 `drafts` 테이블(단일 행)에도 작성 내용을 800ms 디바운스로
저장한다 → 웹뷰 저장소가 비워지거나 앱이 강제 종료돼도 서버 draft에서 복구한다.
채점 완료 시 draft를 정리하되 화면 텍스트는 유지해 제출 직전 내용을 잃지
않는다(`static/app.js`의 `scheduleServerDraftSync`, `loadDraft`).

## 검증

- `tests/test_data_safety.py` (17개): draft 저장/로드/삭제, 기록 개별 삭제,
  백업 생성/목록/키 제거, 복원 라운드트립, 키 보존, 미리보기, 손상 zip 거부,
  경로 조작 차단, 전체 삭제 확인 문구/안전 백업/복구
- 브라우저 preview에서 백업 생성→목록 표시(기록 76건)→복원 실제 클릭 검증
- UI 계획: 현재 설정 화면의 "백업 및 데이터 관리" 섹션에 백업 생성/목록/복원/
  전체 삭제가 모두 구현돼 있다(별도 UI 계획 문서 불필요 — 제품에 통합됨).
