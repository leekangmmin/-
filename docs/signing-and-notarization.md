# 코드 서명·공증 (Phase 6)

## 현재 상태 (정직한 표기)

**이 프로젝트에는 Apple Developer 인증서가 없다.** 따라서:

- ✅ **ad-hoc signed** — 빌드 10단계에서 `codesign --force --deep --sign -`로
  로컬 실행용 ad-hoc 서명이 적용된다(`Signature=adhoc`, `TeamIdentifier=not set`).
- ⏳ **Developer ID signing pending** — 실제 Developer ID Application 인증서 필요
- ⏳ **notarization pending** — Apple 계정 + `xcrun notarytool` 필요
- 🚫 **external distribution prohibited** — Gatekeeper가 ad-hoc/미공증 앱을
  인터넷 다운로드로 표시하면 실행을 막는다. 현재 산출물은 개발자 본인 기기의
  내부 테스트 용도로만 사용한다.

공증을 완료했다고 주장하지 않는다.

## 준비된 스크립트

### `scripts/sign_and_notarize.sh`

인증서를 확보했을 때 실행할 절차를 코드로 문서화했다. 인증서가 없으면
`[SKIP]`으로 안전하게 종료한다(실제로 실행해 skip 동작 확인함). 인증서가
있으면:

1. hardened runtime + `packaging/entitlements.plist`로 deep 서명
2. `codesign --verify --deep --strict`
3. `spctl --assess --type execute`
4. 공증용 zip → `xcrun notarytool submit --wait`
5. `xcrun stapler staple` + validate
6. 최종 Gatekeeper 검증

필요 환경변수(코드/로그에 저장하지 않음):
- `DEVELOPER_ID_APP` — "Developer ID Application: Your Name (TEAMID)"
- `NOTARY_PROFILE` — `notarytool store-credentials`로 저장한 프로파일 이름

### `packaging/entitlements.plist`

hardened runtime용 entitlements. loopback 서버를 위한 `network.server`,
향후 Cloud AI 아웃바운드를 위한 `network.client`를 허용한다(App Sandbox는
현재 off).

## 인증서 확보 후 절차

```bash
export DEVELOPER_ID_APP='Developer ID Application: 이강민 (TEAMID)'
export NOTARY_PROFILE='toefl-notary'
xcrun notarytool store-credentials toefl-notary --apple-id <id> --team-id <TEAMID>
./scripts/build_macos.sh          # ad-hoc RC 빌드
./scripts/sign_and_notarize.sh    # Developer ID 서명 + 공증 + staple
./scripts/make_dmg.sh             # 공증된 앱으로 배포용 DMG
```

이 단계를 완료해야만 "signed / notarized / stapled / Gatekeeper verified"로
표기하고 외부 배포가 가능하다. 그 전까지는 external distribution prohibited.
