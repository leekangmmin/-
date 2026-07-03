"""PyInstaller Analysis 진입 스크립트.

`desktop/launcher.py`를 모듈로 얼려 넣기 위한 최소 wrapper다 — 비즈니스 로직은
전혀 포함하지 않고 `desktop.launcher.main()`을 호출만 한다. PyInstaller는
패키지의 `__main__` 모듈이 아니라 스크립트 파일을 Analysis 진입점으로 요구하므로
이 파일이 필요하다.
"""

from __future__ import annotations

import sys

# desktop/server_manager.py는 uvicorn.Config에 "app.main:app" 문자열을 넘겨
# 런타임에 임포트한다. PyInstaller의 정적 의존성 분석(Analysis)은 이런 문자열
# 기반 임포트를 추적하지 못해 app.main과 그 하위 의존성 전체가 번들에서
# 누락되는 문제가 있었다 — 아래 명시적 임포트로 PyInstaller가 app.main의
# 전체 의존성 트리를 정적으로 발견하도록 강제한다 (런타임 동작에는 영향 없음).
import app.main  # noqa: F401

from desktop.launcher import main

if __name__ == "__main__":
    sys.exit(main())
