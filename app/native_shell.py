"""[DEPRECATED] Phase 5부터 실제 데스크톱 런처는 `desktop/launcher.py`다.

이 모듈은 이전 진입점(`python -m app.native_shell`)과의 하위 호환을 위한
얇은 위임 shim이다. 새 코드는 `desktop.launcher.main`을 직접 쓴다.
"""

from __future__ import annotations

from desktop.launcher import main

if __name__ == "__main__":
    raise SystemExit(main())
