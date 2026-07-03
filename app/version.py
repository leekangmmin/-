"""앱 버전의 단일 출처 (Phase 5).

데스크톱 패키징 메타데이터(Info.plist), health 엔드포인트, 설정 화면,
로그 등 버전 문자열이 필요한 모든 곳이 이 모듈을 참조한다. 여러 곳에
버전을 중복 하드코딩하지 않는다.
"""

from __future__ import annotations

APP_DISPLAY_NAME = "토플첨삭기 by이강민"
APP_BUNDLE_NAME = "TOEFL Writing"
APP_VERSION = "0.6.0"  # Phase 6: internal release candidate
APP_BUILD = "phase6-rc.1"
DB_SCHEMA_VERSION = "1.0.0"
BUNDLE_IDENTIFIER = "com.leekangmin.toeflwriting"
