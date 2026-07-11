# 공개 데모 남용 방지 현황

공개 hosted 데모는 누구나 접속할 수 있으므로 남용 가능성이 있다. 이 문서는
**실제로 구현되고 검증된 것**과 **아직 없는 것**을 정확히 구분한다.

## 구현되고 검증됨

| 방어 | 구현 위치 | 검증 방법 |
|---|---|---|
| 답안 최대 길이(12,000자) | `app/models.py` `EvaluateRequest.essay_text` `max_length` | `tests/test_hosted_web_mode.py::TestRequestSizeLimits` — 초과 시 422 |
| 프롬프트 최대 길이(3,000자) | `app/models.py` `EvaluateRequest.prompt_text` `max_length` | 동일 테스트 파일 |
| 답안 최소 길이(80자/60단어) | `app/models.py`, `app/main.py` | 짧은 답안 400 반환, 기존 테스트에서 검증 |
| admin API 항상 비활성 | `app/main.py` `_require_local_admin_session` — `TOEFL_ADMIN_API_ENABLED=1` 없으면 404 | hosted 모드에서도 404 확인(`test_hosted_web_mode.py`) |
| 클라우드 AI 공개 기본 비활성 | `/api/capabilities`의 `cloud_ai: false` 기본값, `hosted_ai: false` | `TOEFL_WEB_MODE=1`에서도 false 유지 확인 |
| 답안 원문 미로깅 | `uvicorn --no-access-log`(Docker 기본 CMD), FastAPI가 요청 바디를 로그에 남기지 않음 | Docker 컨테이너 로그 실제 확인 — 평가 요청 후 답안 텍스트가 `docker logs`에 없음을 확인함 |
| 프로덕션 stack trace 미노출 | FastAPI 기본 예외 핸들러가 500에서 상세 traceback을 응답 바디에 포함하지 않음(디버그 모드 아님) | 코드 리뷰로 확인, 별도 자동 테스트는 없음 |
| localhost 전용 dashboard | `/api/dashboard`가 `request.client.host`를 검사해 로컬 세션이 아니면 403 | 기존 테스트(`tests/test_admin_api_security.py` 계열)에서 검증 |
| CORS 기본값이 넓지 않음 | `app/main.py`의 `_DEFAULT_ORIGINS`가 `127.0.0.1:8000`/`localhost:8000`만 허용, `TOEFL_EXTRA_ORIGINS`로만 확장 | 코드 확인. hosted 배포 시 실제 도메인을 `TOEFL_EXTRA_ORIGINS`에 명시적으로 추가해야 함(아래 참고) |

## 아직 없음 (정직한 한계)

- **IP별 rate limit** — 구현되지 않았다. 공개 배포 시 nginx/Cloudflare 같은
  리버스 프록시나 PaaS 플랫폼의 rate limit 기능을 반드시 앞단에 둬야 한다.
  애플리케이션 레벨 rate limit은 이번 단계 범위에서 추가하지 않았다(별도
  의존성·저장소가 필요해 범위를 벗어난다고 판단).
- **요청 타임아웃 강제** — FastAPI/uvicorn 레벨의 명시적 타임아웃 미들웨어는
  없다. 채점 자체는 순수 Python 휴리스틱이라 수 밀리초 내에 끝나므로 실무
  리스크는 낮지만, 악의적으로 매우 긴 입력을 반복 전송하면 CPU를 소모할 수
  있다 — 이것이 위 답안 길이 제한(12,000자)의 주된 존재 이유다.
- **계정/세션 기반 격리** — 없음. 여러 사용자가 같은 배포를 공유하면 서로의
  기록을 볼 수 있다(`docs/web-privacy.md` 참고). 공개 다중 사용자 서비스로
  발전시키려면 필수로 추가해야 한다.
- **요청 body 전체 크기 제한(HTTP 레벨)** — Pydantic 필드 `max_length`는
  JSON 파싱 이후에 적용된다. 파싱 자체를 막는 HTTP 레벨 body-size 제한은
  리버스 프록시(nginx `client_max_body_size` 등)에서 설정해야 한다.
- **비용 모니터링/알림** — 클라우드 AI가 기본 비활성이므로 현재는 해당 없음.
  향후 클라우드 AI를 공개 hosted에서 켠다면 `docs/hosted-ai-cost-control.md`의
  비용 게이트를 반드시 먼저 적용해야 한다.

## 배포 시 운영자가 해야 할 최소 조치

1. 리버스 프록시(Caddy/nginx/Cloudflare 등)에 요청 rate limit 설정
2. 실제 배포 도메인을 `TOEFL_EXTRA_ORIGINS` 환경변수에 추가(CORS)
3. `TOEFL_WEB_MODE=1` 설정(공유 서버 기능 숨김)
4. `TOEFL_ADMIN_API_ENABLED`를 설정하지 않음(기본값 유지 = admin 비활성)
5. 클라우드 AI를 켜지 않음(기본값 유지)
6. `docs/web-privacy.md`의 정확한 문구를 UI 어딘가에 노출

## 관련 문서

- `docs/hosted-web-deployment.md`
- `docs/web-privacy.md`
- `docs/hosted-ai-cost-control.md` (클라우드 AI를 나중에 켤 경우)
