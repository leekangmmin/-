# 릴리스 보안 감사 (Phase 6)

빌드 11단계 `scripts/scan_artifact_security.py`가 매 빌드마다 자동 실행하며,
위반 발견 시 빌드를 실패시킨다(exit 1). Phase 6 v0.6.0 산출물 결과: **[PASS]**.

## 자동 스캔 항목 (`scan_artifact_security.py`)

| 검색 | 결과 |
| --- | --- |
| `.env` 파일 | 없음 |
| API 키 패턴 (`sk-`, `sk-ant-`, `AIza`) — 텍스트/설정 파일 | 없음 |
| `.db` / `.sqlite` 파일 | 없음 |
| Git 메타데이터 (.git, .gitignore) | 없음 |
| 테스트 산출물 (pytest_cache, conftest, test_*.py) | 없음 |
| 개발 파일 (screenshot, *.log) | 없음 |
| 전문가/마이그레이션 백업 데이터 | 없음 |
| PYZ bytecode의 개발 절대경로(`/Users/<home>`) 유출 | 없음 (상대경로만) |

## 로컬 실행 보안 (패키징 앱 실행 확인)

| 항목 | 결과 |
| --- | --- |
| 서버 bind | `127.0.0.1`만 (`desktop/server_manager.py` HOST 상수) |
| `0.0.0.0` / LAN 노출 | 없음 |
| admin API 기본값 | `GET /api/expert-data/summary`, `/api/shadow/summary` → 404 |
| shadow mode 기본값 | `/api/health`의 `shadow_enabled=false` |
| health 응답 민감정보 | 없음 (버전/오프라인가용성/shadow불리언만) |
| Offline Core 외부 요청 | 없음 (정적 자산에 외부 URL 0건, CDN 제거됨) |

## 백업 파일 보안

- 백업 zip의 `submissions.db`는 API 키를 제거한 사본(`DELETE` + `VACUUM`으로
  물리적 제거) — 백업이 타인에게 전달돼도 키가 유출되지 않음
- 복원 시 경로 조작(`../`) 차단 — backups_dir 안의 파일명만 허용
- 자동 테스트 `tests/test_data_safety.py`가 키 제거·경로 차단을 회귀 검증

## 로그

- `desktop/server_manager.py`는 uvicorn `access_log=False`로 요청 경로가 답안
  원문과 섞여 기록되지 않게 함
- 답안 원문·API 키·전문가 데이터를 로그에 남기지 않음

## 산출물 파일 목록/크기

```text
전체: 101.7MB (.app), 44.5MB (zip), 30MB (dmg)
Contents/MacOS/TOEFL Writing        실행 파일
Contents/Resources/app.icns          앱 아이콘
Contents/Resources/static/           index.html, app.js, styles.css (3개만)
Contents/Frameworks/                 Python.framework, WebKit, uvloop 등
Contents/Info.plist                  version=0.6.0, id=com.leekangmin.toeflwriting
Contents/_CodeSignature/             ad-hoc 서명
```

## 한계 (정직한 표기)

- 서드파티 컴파일 확장 모듈(`pydantic_core`, `uvloop` 등 `.so`)의 내부
  문자열은 전수 검사하지 않음 — PyPI 공개 wheel 그대로이며 프로젝트 고유
  비밀정보가 담길 경로가 없음
- codesign 서명 체인의 신뢰성은 검증하지 않음 (현재 ad-hoc)
