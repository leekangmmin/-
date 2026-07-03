#!/bin/zsh
# Developer ID 코드 서명 + 공증 스크립트 (Apple Developer 인증서 보유 시에만 실행).
#
# 현재 상태: 이 프로젝트에는 Apple Developer 인증서가 없다. 이 스크립트는
# 인증서를 확보했을 때 실행할 절차를 코드로 문서화한 것이며, 인증서 없이
# 실행하면 [SKIP]으로 안전하게 종료한다. codesign/notarization을 완료했다고
# 주장하지 않는다 (docs/signing-and-notarization.md 참고).
#
# 사용 전 필요한 환경변수:
#   DEVELOPER_ID_APP   — "Developer ID Application: Your Name (TEAMID)"
#   NOTARY_PROFILE     — xcrun notarytool store-credentials로 저장한 프로파일 이름
#
# 인증 정보(Apple ID, 앱 암호, 인증서)는 이 스크립트나 로그에 저장하지 않는다.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_PATH="$PROJECT_DIR/dist/토플첨삭기 by이강민.app"
# 실제 번들 이름은 app.version의 APP_BUNDLE_NAME 기준 — dist에서 탐색
if [ ! -d "$APP_PATH" ]; then
  APP_PATH=$(find "$PROJECT_DIR/dist" -maxdepth 1 -name "*.app" | head -1)
fi
ENTITLEMENTS="$PROJECT_DIR/packaging/entitlements.plist"

echo "==> Developer ID 인증서 확인"
if ! security find-identity -v -p codesigning 2>/dev/null | grep -q "Developer ID Application"; then
  echo "[SKIP] Developer ID Application 인증서가 없습니다."
  echo "       현재 상태: unsigned / ad-hoc signed internal release candidate"
  echo "       codesign pending / notarization pending / external distribution prohibited"
  echo ""
  echo "       인증서를 확보하면 다음 환경변수를 설정하고 이 스크립트를 다시 실행하세요:"
  echo "         export DEVELOPER_ID_APP='Developer ID Application: Your Name (TEAMID)'"
  echo "         export NOTARY_PROFILE='your-notary-profile'"
  exit 0
fi

: "${DEVELOPER_ID_APP:?DEVELOPER_ID_APP 환경변수를 설정하세요}"
: "${NOTARY_PROFILE:?NOTARY_PROFILE 환경변수를 설정하세요}"

echo "==> hardened runtime + entitlements로 deep 서명"
codesign --force --deep --options runtime \
  --entitlements "$ENTITLEMENTS" \
  --sign "$DEVELOPER_ID_APP" \
  "$APP_PATH"

echo "==> 서명 검증"
codesign --verify --deep --strict --verbose=2 "$APP_PATH"
spctl --assess --type execute --verbose=2 "$APP_PATH" || echo "[WARN] spctl 평가 실패 — 공증 후 다시 확인"

echo "==> 공증용 zip 생성"
NOTARIZE_ZIP="$PROJECT_DIR/dist/notarize-upload.zip"
ditto -c -k --keepParent "$APP_PATH" "$NOTARIZE_ZIP"

echo "==> notarytool submit (완료까지 대기)"
xcrun notarytool submit "$NOTARIZE_ZIP" --keychain-profile "$NOTARY_PROFILE" --wait

echo "==> staple"
xcrun stapler staple "$APP_PATH"
xcrun stapler validate "$APP_PATH"

echo "==> 최종 Gatekeeper 검증"
spctl --assess --type execute --verbose=2 "$APP_PATH"

echo ""
echo "[완료] signed / notarized / stapled / Gatekeeper verified"
