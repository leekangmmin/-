# 릴리스 체크리스트

## 공통

- [ ] `git status`가 의도한 변경만 보여준다.
- [ ] `git diff --check` 통과.
- [ ] `.venv/bin/python -m pytest tests/ -q` 통과.
- [ ] `.venv/bin/python -m tests.eval_harness` 통과.
- [ ] `.venv/bin/python scripts/run_local_ai_validation.py --dry-run` 통과.
- [ ] `.venv/bin/python scripts/run_local_ai_validation.py --provider rule --fixture grammar_errors --limit 2` 통과.
- [ ] `git ls-tree -r --name-only HEAD`에서 DB, `.env`, 모델, `.app`, `.dmg`, `.exe`, `.msi`, `.zip`, 로그, 임시 보고서가 추적되지 않는다.
- [ ] release notes 작성.
- [ ] checksum 생성.
- [ ] 알려진 한계를 release notes에 포함.

## Windows

- [ ] Windows 머신에서 `.\windows\build_windows.ps1` 통과.
- [ ] 앱이 console 없이 실행된다.
- [ ] 서버는 `127.0.0.1`에만 바인딩한다.
- [ ] 동적 포트를 사용한다.
- [ ] 중복 실행 방지와 종료 후 고아 프로세스 없음 확인.
- [ ] evaluate, history, dashboard, PDF, backup/restore, draft, Build a Sentence 확인.
- [ ] `/api/local-ai/status` 확인.
- [ ] API 키 없이 core 기능 확인.
- [ ] artifact security scan 통과.
- [ ] 서명 전 SmartScreen 경고를 known limitation에 명시.

## macOS

- [ ] macOS 빌드 스크립트 통과.
- [ ] `.app` smoke test 통과.
- [ ] DMG 또는 ZIP 생성.
- [ ] artifact security scan 통과.
- [ ] Developer ID 서명과 notarization 여부를 실제 상태대로 표기.

## Web

- [ ] `/api/capabilities` 응답 확인.
- [ ] 360, 390, 430, 768, 834, 1024, 1280, 1440px viewport에서 주요 UI 확인.
- [ ] hosted deployment 전 HTTPS, rate limit, data policy 확인.
- [ ] PWA라고 표기하려면 manifest/service worker/installability 검증 필요.
