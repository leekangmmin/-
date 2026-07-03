# 사용자 데이터 경로와 마이그레이션 (Phase 5)

## 저장 위치

앱 패키지 내부나 현재 작업 디렉터리에 사용자 데이터를 저장하지 않는다.
`platformdirs`로 OS 표준 사용자 데이터 경로를 사용한다(`app/paths.py`).

### macOS (실제 구현, 검증됨)

```text
~/Library/Application Support/TOEFL Writing/
├─ databases/
│  ├─ submissions.db
│  ├─ shadow_assessments.db
│  └─ expert_data.db
├─ exports/
│  └─ reports/        (PDF)
├─ backups/
├─ logs/
├─ config/
│  └─ app.lock         (SingleInstanceLock)
└─ migrations/
```

`APP_NAME = "TOEFL Writing"`(`app/paths.py`)가 `platformdirs.user_data_dir()`에
전달되는 실제 폴더명이다.

### Windows (향후 대응, 미검증)

`platformdirs`는 Windows에서 자동으로 `%LOCALAPPDATA%\TOEFL Writing\`를
반환하도록 설계돼 있으나, **Windows 환경에서 실제로 실행해 확인하지는
않았다** — 현재 macOS 환경에서만 검증 가능하다.

## 경로 우선순위

```python
def user_data_dir() -> Path:
    override = _env_override()      # 1. TOEFL_DATA_DIR 환경변수 (테스트/개발 override)
    if override is not None:
        ...
    path = Path(platformdirs.user_data_dir(APP_NAME, appauthor=False))  # 2. OS 기본 경로
    ...
```

`tests/conftest.py`가 모든 pytest 실행에 대해 `TOEFL_DATA_DIR`을 임시 디렉터리로
강제 설정한다 — 어떤 테스트도 실제 macOS 사용자 데이터 경로를 건드리지
않는다. 운영 앱(패키징 모드, 개발 모드 모두)은 이 환경변수를 설정하지
않으므로 항상 OS 기본 경로를 쓴다 — 프로젝트 루트의 `data/`를 사용하지
않는다.

## 데이터 구분

프로덕션 사용자 기록(`submissions.db`), shadow 결과(`shadow_assessments.db`),
전문가 데이터(`expert_data.db`)를 별도 DB 파일로 분리했다(기존에도 분리돼
있었고, Phase 5에서 위치만 `databases_dir()`로 옮겼다). 로그/PDF
exports/백업/설정도 각각 별도 하위 폴더를 쓴다.

## 기존 데이터 마이그레이션 (`app/data_migration.py`)

### 배경

Phase 4까지는 DB가 프로젝트 루트의 `data/`(`app/db.py`의 구
`DB_PATH = BASE_DIR / "data" / "submissions.db"` 등)에 있었다. Phase 5에서
사용자 데이터 경로를 OS 표준 위치로 옮기면서, 기존에 그 위치에 쌓인 실제
기록을 잃어버리지 않도록 1회성 마이그레이션을 구현했다.

### 안전 원칙 (구현 상태)

- **원본 삭제 금지**: `_migrate_single_db()`는 `sqlite3.Connection.backup()` API로
  일관된 스냅샷을 새 위치에 복사할 뿐, 원본 파일을 절대 지우지 않는다.
- **backup 우선**: 마이그레이션 시작 전 `data/.migration_backup_v1/`에 원본의
  백업 복사본을 만든다(`.gitignore`에 이 경로를 추가해 커밋 방지).
- **record count 검증**: 복사 후 `sqlite_master`를 통해 얻은 테이블별 row
  count가 원본과 일치하는지 확인한 뒤에만 성공으로 표시한다.
- **기존 목적지 덮어쓰지 않음**: 새 사용자 데이터 경로에 이미 같은 이름의 DB가
  있으면 마이그레이션을 건너뛴다(사용자가 이미 새 위치에서 앱을 써서 데이터가
  쌓인 경우 구 데이터로 덮어쓰지 않음).
- **부분 성공 = 미완료 처리**: 3개 DB(`submissions.db`, `shadow_assessments.db`,
  `expert_data.db`) 중 일부만 성공하면 완료 마커를 쓰지 않는다 — 다음 실행 시
  실패한 것만 자동으로 재시도한다(`legacy_data_migration_v1.complete` 마커
  파일로 전체 성공 여부를 기록).
- **schema mismatch 무시하지 않음**: row count 불일치나 예외 발생 시 해당 DB는
  실패로 기록되고 조용히 넘어가지 않는다.

### 실행 시점

`app/main.py`의 FastAPI startup 이벤트에서 `init_db()`보다 먼저 실행된다:

```python
@app.on_event("startup")
def startup() -> None:
    from app.data_migration import migrate_legacy_data_if_needed
    migrate_legacy_data_if_needed()
    init_db()
```

즉 개발 모드/패키징 모드 관계없이 서버가 뜰 때마다 자동으로 검사하되,
이미 마이그레이션 완료 마커가 있으면 아무 것도 하지 않는다(중복 마이그레이션
방지).

### 테스트

`tests/test_data_migration.py` (10개) — legacy 없음 시 noop, 2회 호출 시
noop, row count 일치 복사, 원본 미삭제, 완료 마커 타이밍, 백업 생성, 기존
목적지 미덮어쓰기, 부분 실패 시 마커 미기록, 부분 실패 후 재시도 성공까지
전부 커버한다.

## 앱 업데이트 시 데이터 보존

패키징된 `.app`을 교체(새 빌드로 덮어쓰기)해도 사용자 데이터는
`~/Library/Application Support/TOEFL Writing/`에 있으므로 영향받지 않는다 —
`.app` 번들 자체는 무상태(stateless)다. `scripts/packaged_app_smoke_test.py`의
"재실행 — 이전 기록 유지" 단계가 이를 실증한다(단, 이는 같은 빌드를 재실행한
것이지 "구버전 빌드 → 신버전 빌드 교체" 시나리오까지 실제로 재현하지는
않았다 — 동일한 데이터 경로 설계이므로 결과가 다를 이유는 없지만, 이 구체
시나리오는 직접 검증하지 않은 이론적 결론임을 밝혀둔다).

## 백업·복원 (내부 알파 범위)

Phase 5에서는 마이그레이션에 필요한 백업 인프라(`sqlite3 .backup()` 기반
일관된 스냅샷, row-count 검증)만 구현했다. 사용자가 임의 시점에 수동으로
호출할 수 있는 백업/복원 API나 UI는 아직 만들지 않았다 — 이는 현재 한계로
남겨둔다(`docs/phase5-audit.md`의 "현재 한계" 참고).
