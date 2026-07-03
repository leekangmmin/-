# macOS 릴리스 빌드 파이프라인 (Phase 6)

## 빌드 명령

```bash
./scripts/build_macos.sh
```

전용 `.build-venv`를 매번 새로 만들어 사용자 개발 venv와 분리한다(clean build).
14단계를 순서대로 실행하며, 어느 단계라도 실패하면 즉시 중단된다(`set -euo pipefail`).

| 단계 | 내용 |
| --- | --- |
| 1 | build/dist 정리 |
| 2 | build venv 생성 (python3.11) |
| 3 | 의존성 + pyinstaller + pytest 설치 |
| 4 | py_compile (app/desktop/scripts) |
| 5 | **pytest 전체 (237개 통과 게이트)** |
| 6 | eval_harness (품질 회귀 게이트) |
| 7 | 앱 아이콘 확인/생성 |
| 8 | PyInstaller one-dir 빌드 |
| 9 | Info.plist 검증 (버전/식별자/아이콘 = app.version 단일 출처) |
| 10 | ad-hoc 코드 서명 |
| 11 | **artifact 보안 스캔** (비밀정보/DB/개발경로) |
| 12 | **패키징 앱 smoke test** (최초실행~재시작~종료) |
| 13 | **업데이트 데이터 보존 테스트** (구버전→신버전) |
| 14 | release manifest + checksum + zip |

## 산출물 (dist/)

| 파일 | 설명 |
| --- | --- |
| `TOEFL Writing.app` | 앱 번들 (101.7MB) |
| `TOEFL-Writing-macOS-0.6.0.zip` | 앱 압축본 (44.5MB) |
| `release-manifest.json` | 버전/커밋/빌드환경/서명상태 |
| `checksums.txt` | zip·manifest의 SHA-256 |
| `TOEFL-Writing-macOS-0.6.0.dmg` | 내부 테스트용 DMG (30MB, `make_dmg.sh` 별도 실행) |

모두 `dist/`에 생성되며 `.gitignore`로 Git에서 제외된다(재현 가능한 빌드이므로
커밋하지 않고 release artifact로 별도 보관).

## release manifest 내용

```json
{
  "app_name": "토플첨삭기 by이강민",
  "app_version": "0.6.0",
  "build_version": "phase6-rc.1",
  "git_commit": "<HEAD>",
  "python_version": "3.11.15",
  "pyinstaller_version": "6.21.0",
  "dependency_lock_hash": "<requirements.txt sha256[:16]>",
  "artifact_size_bytes": 101741221,
  "zip_size_bytes": 44547166,
  "signing_status": "ad-hoc signed (Developer ID pending)",
  "notarization_status": "pending (Apple Developer 인증서 필요)",
  "distribution": "internal release candidate — external distribution prohibited"
}
```

## 아이콘

`scripts/generate_app_icon.py`가 자체 제작 디자인(파란 배경 + 흰 답안지 +
녹색 체크 배지, Pillow로 그림)을 1024px 마스터 → 10종 iconset → `iconutil`로
`app.icns` 변환. TOEFL/ETS/토스 로고를 쓰지 않는다. spec의 `BUNDLE(icon=...)`과
Info.plist `CFBundleIconFile`에 연결되며, 빌드 9단계에서 실제 번들에 존재함을
검증한다.

## 버전 단일 출처

`app/version.py`의 `APP_VERSION`/`BUNDLE_IDENTIFIER`를 spec, Info.plist,
manifest, health 엔드포인트가 모두 참조한다. `verify_info_plist.py`가 빌드마다
불일치를 잡는다(Phase 6: 0.5.0 → 0.6.0).
