# Xcode 앱 프로젝트 가이드

이 디렉터리는 Swift Package 기반 앱과 함께, 정식 Xcode 앱 프로젝트를 생성할 수 있는 설정을 포함합니다.

## 포함된 파일

- `project.yml`: xcodegen 프로젝트 정의
- `Info.plist`: Xcode 앱 번들 정보
- `ToeflNativeApp.entitlements`: 앱 샌드박스/네트워크 권한
- `Assets.xcassets`: AppIcon 자산 카탈로그
- `exportOptions.plist`: 아카이브 내보내기 옵션

## 빠른 시작

1. `brew install xcodegen`
2. `cd NativeMacApp`
3. `xcodegen generate --spec project.yml`
4. `open ToeflNativeApp.xcodeproj`

## 서명 설정

Xcode에서 아래를 설정하세요.

- Signing & Capabilities > Team
- Bundle Identifier (기본: `com.lee.gangmin.toefl-native`)
- Developer ID 배포 시 `exportOptions.plist`의 `teamID` 값

## 아이콘 설정

`Assets.xcassets/AppIcon.appiconset` 안에 macOS 아이콘(16~1024)을 채워 넣으세요.

## 아카이브/내보내기

프로젝트 루트에서 아래 스크립트를 실행하면 생성/아카이브/내보내기를 자동 처리합니다.

- `./macos/build_xcode_app.command`
