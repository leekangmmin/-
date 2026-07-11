#!/bin/bash
# Docker 이미지 sanity test — 실제 빌드하고 컨테이너를 띄워 핵심 엔드포인트를
# 검증한다. Windows/macOS/Linux 어디서든 Docker만 있으면 이 앱을 쓸 수 있음을
# 재현 가능하게 증명하는 스크립트다.
#
# usage: ./scripts/docker_sanity_test.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

IMAGE="toefl-writing-scorer:sanity"
CONTAINER="toefl-web-sanity-$$"
PORT=18099

cleanup() {
  docker stop "$CONTAINER" >/dev/null 2>&1 || true
  docker rm "$CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "==> [1/6] docker build"
docker build -t "$IMAGE" .

echo "==> [2/6] 컨테이너 실행 (hosted web 모드, TOEFL_WEB_MODE=1)"
docker run -d --name "$CONTAINER" -p "${PORT}:8000" -e TOEFL_WEB_MODE=1 "$IMAGE" >/dev/null

echo "==> [3/6] health check 대기"
for _ in $(seq 1 20); do
  if curl -sf "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
curl -sf "http://127.0.0.1:${PORT}/api/health" | grep -q '"status":"ok"' \
  && echo "    OK: /api/health" || { echo "    [FAIL] health check"; exit 1; }

echo "==> [4/6] capabilities — hosted web 모드 확인"
CAPS=$(curl -sf "http://127.0.0.1:${PORT}/api/capabilities")
echo "$CAPS" | grep -q '"mode":"web"' && echo "    OK: mode=web" || { echo "    [FAIL] mode != web"; exit 1; }
echo "$CAPS" | grep -q '"local_ai":false' && echo "    OK: local_ai hidden" || { echo "    [FAIL]"; exit 1; }
echo "$CAPS" | grep -q '"admin_api":false' && echo "    OK: admin_api disabled" || { echo "    [FAIL]"; exit 1; }

echo "==> [5/6] admin API 실제 404 확인"
CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${PORT}/api/expert-data/summary")
[ "$CODE" = "404" ] && echo "    OK: admin endpoint 404" || { echo "    [FAIL] got $CODE"; exit 1; }

echo "==> [6/6] 평가 + PDF (한글 폰트 포함)"
ESSAY='Universities should invest more resources in mental health support for students because academic pressure has increased significantly in recent years. Many students struggle silently with anxiety and stress, and without adequate counseling services their academic performance and overall wellbeing suffer considerably. Providing accessible mental health resources on campus would help students manage these challenges early, before they escalate into more serious problems that affect graduation rates and long-term career success.'
RESP=$(curl -sf -X POST "http://127.0.0.1:${PORT}/api/evaluate" -H "Content-Type: application/json" -d "{\"essay_text\": $(python3 -c "import json,sys;print(json.dumps(sys.argv[1]))" "$ESSAY")}")
SUBID=$(echo "$RESP" | python3 -c "import json,sys;print(json.load(sys.stdin)['submission_id'])")
echo "    OK: evaluate → submission_id=$SUBID"
PDF_CODE=$(curl -s -o /tmp/docker-sanity-report.pdf -w "%{http_code}" "http://127.0.0.1:${PORT}/api/report/${SUBID}.pdf")
[ "$PDF_CODE" = "200" ] && echo "    OK: PDF 생성 ($(wc -c < /tmp/docker-sanity-report.pdf) bytes)" || { echo "    [FAIL] PDF $PDF_CODE"; exit 1; }
rm -f /tmp/docker-sanity-report.pdf

echo ""
echo "[PASS] Docker sanity test 전체 통과"
