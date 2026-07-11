# syntax=docker/dockerfile:1
# 토플 라이팅 채점기 — hosted web / self-host 컨테이너.
#
# 이 이미지는 pywebview 데스크톱 셸을 포함하지 않는다 — FastAPI 서버만 실행해
# 어떤 OS의 브라우저에서든(Windows 포함) 접속할 수 있게 한다. 데스크톱 전용
# 기능(네이티브 창, 로컬 AI 프로세스 관리)은 이미지에 포함하지 않는다.
#
# 기본값(TOEFL_WEB_MODE 미설정)은 1인 self-host 기준으로 전체 기능(로컬 AI
# 패널·백업/복원 UI 포함)을 노출한다. 여러 명이 접속하는 공개 hosted 배포라면
# TOEFL_WEB_MODE=1을 설정해 desktop 전용/공유 서버에 부적절한 기능(로컬 파일
# 백업·복원 UI, 로컬 AI 패널)을 숨겨라 — 자세한 내용은
# docs/hosted-web-deployment.md 참고.

FROM python:3.11-slim AS runtime

# fonts-noto-cjk: PDF 리포트의 한글 텍스트가 Linux 컨테이너에서도 깨지지 않게
# 한다(app/main.py의 unicode_candidates가 이 패키지의 표준 설치 경로를 찾는다).
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 런타임에 실제로 필요한 것만 복사한다 — 테스트/빌드 스크립트/데스크톱 패키징/
# 문서/Windows 런처는 이미지에 포함하지 않는다(.dockerignore가 1차 방어선이고
# 여기서 필요한 디렉터리만 명시적으로 재확인 복사한다).
COPY app ./app
COPY static ./static

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /home/appuser/.local/share \
    && chown -R appuser:appuser /srv/app /home/appuser
USER appuser

# platformdirs가 컨테이너 안에서 사용자 데이터 경로를 잡을 수 있도록 HOME을
# 명시한다. 볼륨을 마운트하지 않으면 컨테이너 재생성 시 데이터가 사라진다
# (ephemeral) — docs/hosted-web-deployment.md에 영속화 방법을 안내한다.
ENV HOME=/home/appuser \
    PYTHONUNBUFFERED=1 \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/api/health', timeout=3)" || exit 1

# $PORT를 셸 확장으로 반영해야 하므로 shell form을 쓴다(exec form은 변수
# 확장이 되지 않는다). host는 컨테이너 밖 접속을 위해 0.0.0.0으로 바인딩한다
# — 이는 데스크톱 모드(127.0.0.1 전용)와 의도적으로 다른, hosted 전용 설정이다.
CMD uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --no-access-log
