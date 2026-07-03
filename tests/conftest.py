"""테스트 세션 전체에서 실제 OS 사용자 데이터 경로(~/Library/Application Support/...)를
절대 건드리지 않도록, 모듈 임포트보다 먼저 TOEFL_DATA_DIR을 임시 디렉터리로
고정한다. `app.paths.user_data_dir()`는 이 환경변수를 최우선으로 확인하므로,
이 파일이 다른 어떤 `app.*` 모듈보다 먼저 로드되는 것이 중요하다 (pytest는
같은 디렉터리의 conftest.py를 테스트 모듈 수집보다 먼저 임포트한다).
"""

from __future__ import annotations

import os
import tempfile

if "TOEFL_DATA_DIR" not in os.environ:
    _session_tmp_dir = tempfile.mkdtemp(prefix="toefl_pytest_data_")
    os.environ["TOEFL_DATA_DIR"] = _session_tmp_dir
