# Hosted Web 배포 가이드

목표: **Windows 실행 파일이 없어도**, Docker만 있으면 어떤 OS에서든 브라우저로
이 앱을 쓸 수 있게 한다. 이 문서는 실제로 빌드하고 실행해서 검증한 절차만
담는다 — 검증하지 않은 플랫폼은 "미검증"으로 명시한다.

## 1. Docker로 바로 실행 (검증됨)

```bash
git clone https://github.com/leekangmmin/-.git toefl-writing-scorer
cd toefl-writing-scorer

docker build -t toefl-writing-scorer .
docker run -p 8000:8000 toefl-writing-scorer
```

브라우저에서 `http://localhost:8000` 을 연다. Windows(Docker Desktop),
macOS, Linux 어디서든 동일하게 동작한다 — **Python 설치도, Windows 전용
빌드도 필요 없다.**

### 실제 검증 내역 (`scripts/docker_sanity_test.sh`)

- `docker build` 성공 (이미지 크기 약 540MB)
- `/api/health` → 200
- `/api/capabilities` → hosted 모드에서 `mode: "web"`, `local_ai: false`,
  `admin_api: false`
- `/api/expert-data/summary`(admin) → 404
- 답안 평가 → 성공, 제출 ID 발급
- PDF 리포트 생성 → 성공, **한글 텍스트가 실제로 렌더링됨**(컨테이너에
  `fonts-noto-cjk` 설치, `pdftotext`로 한글 문자열 추출 확인)
- graceful stop → 정상 종료

재현: `./scripts/docker_sanity_test.sh`

### 데이터 영속화 (선택)

기본적으로 컨테이너를 재생성하면 SQLite 데이터가 사라진다(ephemeral).
유지하려면 볼륨을 마운트한다:

```bash
docker run -p 8000:8000 \
  -v toefl-data:/home/appuser/.local/share \
  toefl-writing-scorer
```

**주의**: 볼륨을 마운트해도 계정 시스템이 없으므로 이 컨테이너에 접속하는
모든 사용자가 같은 데이터를 공유한다(`docs/web-privacy.md` 참고). 개인
용도로 자체 호스팅할 때만 권장한다.

### hosted web 모드 활성화

여러 명이 접속하는 공개 배포라면 데스크톱 전용/공유 서버에 부적절한 기능
(로컬 AI 패널, 로컬 파일 백업·복원 UI)을 숨긴다:

```bash
docker run -p 8000:8000 -e TOEFL_WEB_MODE=1 toefl-writing-scorer
```

## 2. 일반적인 PaaS에 배포 (미검증, 명령어만 안내)

아래 플랫폼에 실제로 배포해 검증하지는 않았다. Dockerfile을 그대로 쓰는
표준 컨테이너 배포 방식이므로 동작할 것으로 예상하지만, "검증됨"이라고
주장하지 않는다.

### Render / Railway / Fly.io류 (Docker 기반)

이런 플랫폼은 보통 저장소의 `Dockerfile`을 자동 감지해 빌드한다. 별도
설정 파일 없이도 동작할 가능성이 높다. 필요한 최소 설정:

- **빌드**: Dockerfile 자동 감지 (별도 buildpack 불필요)
- **포트**: 플랫폼이 주입하는 `$PORT` 환경변수를 그대로 사용(Dockerfile의
  `CMD`가 이미 `$PORT`를 읽는다)
- **환경변수**: `TOEFL_WEB_MODE=1` (공개 배포 권장), `TOEFL_EXTRA_ORIGINS`
  (실제 도메인)
- **영속 스토리지**: 플랫폼이 제공하는 볼륨/디스크 기능을 `/home/appuser/.local/share`
  에 마운트

플랫폼별 전용 설정 파일(`render.yaml`, `fly.toml` 등)은 실제 계정으로
검증하지 않은 상태에서 만들면 잘못된 필드로 오히려 혼란을 줄 수 있어
이번 단계에서는 만들지 않았다. 각 플랫폼의 "Dockerfile 배포" 공식 문서를
따르는 것을 권장한다.

### Hugging Face Spaces (Docker SDK)

Spaces는 `Dockerfile`이 있는 저장소를 Docker SDK로 그대로 빌드할 수 있다.
Space 설정에서 SDK를 `docker`로 지정하고 포트를 `8000`으로 맞추면 이론상
동작한다 — **실제 Space에 배포해 검증하지는 않았다.**

## 3. 셀프호스트 VPS (미검증, 절차만 안내)

```bash
# VPS에 Docker 설치 후
git clone https://github.com/leekangmmin/-.git
cd -
docker build -t toefl-writing-scorer .
docker run -d --name toefl -p 8000:8000 -e TOEFL_WEB_MODE=1 \
  -v toefl-data:/home/appuser/.local/share \
  --restart unless-stopped \
  toefl-writing-scorer

# 리버스 프록시(예: Caddy)로 HTTPS + rate limit 적용 — 필수
```

HTTPS와 rate limit은 이 프로젝트 범위 밖이며 리버스 프록시가 반드시
담당해야 한다(`docs/public-demo-safety.md` 참고).

## 4. 로컬 LAN 자체 호스팅 (검증됨, Docker 없이도 가능)

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

같은 Wi-Fi/LAN 안의 다른 기기에서 `http://<이 컴퓨터의 IP>:8000`으로
접속할 수 있다. `--host 0.0.0.0`은 데스크톱 모드(`127.0.0.1` 전용)와
의도적으로 다른 설정이며, 신뢰하는 사설 네트워크에서만 사용해야 한다.

## 사용 방법 자체는 다른 문서 참고

일단 서버가 뜬 뒤 "어떤 기능을 쓸 수 있는지"는 `docs/web-user-guide.md`,
반응형/모바일 상태는 `docs/mobile-tablet-ui-audit.md`를 참고한다.

## 관련 문서

- `docs/web-privacy.md` — hosted 개인정보 처리
- `docs/public-demo-safety.md` — 남용 방지 현황과 한계
- `docs/web-user-guide.md` — 실행 후 사용법
- `docs/web-deployment-plan.md` — 단계별 배포 로드맵(1단계/2단계/3단계 개념)
