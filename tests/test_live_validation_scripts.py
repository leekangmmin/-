"""scripts/run_real_shadow_validation.py, scripts/run_real_provider_injection_test.py의
비용 게이트가 실제로 안전하게 동작하는지 검증한다.

이 테스트들은 절대 실제 Anthropic API를 호출하지 않는다 — 플래그/환경변수 조건이
빠졌을 때 스크립트가 확실히 dry-run으로 멈추는지, 그리고 조건이 충족돼도
provider가 사용 불가능하면(API 키 없음) 안전하게 abort하는지만 확인한다.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SHADOW_VALIDATION_SCRIPT = PROJECT_ROOT / "scripts" / "run_real_shadow_validation.py"
INJECTION_SCRIPT = PROJECT_ROOT / "scripts" / "run_real_provider_injection_test.py"
PYTHON = sys.executable


def _clean_env() -> dict[str, str]:
    env = dict(os.environ)
    for key in ("ANTHROPIC_API_KEY", "TOEFL_SHADOW_ENABLED", "TOEFL_SHADOW_PROVIDER"):
        env.pop(key, None)
    return env


def _run(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PYTHON, *args], cwd=PROJECT_ROOT, env=env,
        capture_output=True, text=True, timeout=30,
    )


class TestShadowValidationRunnerGate:
    def test_no_flags_is_dry_run_only_and_exits_zero(self):
        result = _run([str(SHADOW_VALIDATION_SCRIPT), "--limit", "1"], _clean_env())
        assert result.returncode == 0
        assert "DRY RUN" in result.stdout
        assert "실제 API 호출을 수행하지 않는다" in result.stdout

    def test_explicit_dry_run_flag_never_calls_network(self):
        result = _run([str(SHADOW_VALIDATION_SCRIPT), "--limit", "1", "--dry-run",
                        "--i-understand-this-costs-money", "--max-estimated-cost-usd", "5.0"], _clean_env())
        assert result.returncode == 0
        assert "DRY RUN" in result.stdout

    def test_missing_api_key_aborts_even_with_all_flags(self):
        env = _clean_env()
        env["TOEFL_SHADOW_ENABLED"] = "1"
        env["TOEFL_SHADOW_PROVIDER"] = "claude"
        result = _run([str(SHADOW_VALIDATION_SCRIPT), "--limit", "1",
                        "--max-estimated-cost-usd", "1.0", "--i-understand-this-costs-money"], env)
        assert result.returncode == 1
        assert "ABORT" in result.stdout
        assert "missing_api_key" in result.stdout

    def test_shadow_disabled_aborts_even_with_cost_flags(self):
        env = _clean_env()
        env["ANTHROPIC_API_KEY"] = "sk-ant-fake-not-real"
        result = _run([str(SHADOW_VALIDATION_SCRIPT), "--limit", "1",
                        "--max-estimated-cost-usd", "1.0", "--i-understand-this-costs-money"], env)
        assert result.returncode == 1
        assert "shadow_disabled" in result.stdout

    def test_budget_exceeded_aborts_before_any_call_even_with_key_present(self):
        env = _clean_env()
        env["ANTHROPIC_API_KEY"] = "sk-ant-fake-not-real"
        env["TOEFL_SHADOW_ENABLED"] = "1"
        env["TOEFL_SHADOW_PROVIDER"] = "claude"
        result = _run([str(SHADOW_VALIDATION_SCRIPT), "--limit", "50",
                        "--max-estimated-cost-usd", "0.001", "--i-understand-this-costs-money"], env)
        assert result.returncode == 1
        assert "ABORT" in result.stdout
        assert "예상 비용" in result.stdout

    def test_unknown_provider_name_aborts(self):
        env = _clean_env()
        env["ANTHROPIC_API_KEY"] = "sk-ant-fake-not-real"
        env["TOEFL_SHADOW_ENABLED"] = "1"
        env["TOEFL_SHADOW_PROVIDER"] = "not-a-real-provider"
        result = _run([str(SHADOW_VALIDATION_SCRIPT), "--limit", "1",
                        "--max-estimated-cost-usd", "1.0", "--i-understand-this-costs-money"], env)
        assert result.returncode == 1
        assert "unknown_provider" in result.stdout

    def test_never_prints_essay_text_in_dry_run(self):
        result = _run([str(SHADOW_VALIDATION_SCRIPT), "--limit", "2"], _clean_env())
        # 원문 노출 여부는 직접 검증할 수 없지만(제출 데이터가 없을 수도 있음),
        # 최소한 명시적으로 "원문 미노출"을 표시하고 essay_text 필드명을 찍지 않는지 확인
        assert "essay_text" not in result.stdout
        assert "response_text" not in result.stdout


class TestInjectionScriptGate:
    def test_no_flags_is_dry_run_only(self):
        result = _run([str(INJECTION_SCRIPT), "--limit", "1"], _clean_env())
        assert result.returncode == 0
        assert "DRY RUN" in result.stdout

    def test_missing_cost_flag_is_dry_run_even_with_consent_flag(self):
        result = _run([str(INJECTION_SCRIPT), "--limit", "1", "--i-understand-this-costs-money"], _clean_env())
        assert result.returncode == 0
        assert "DRY RUN" in result.stdout

    def test_all_flags_but_no_api_key_aborts_cleanly(self):
        env = _clean_env()
        env["TOEFL_SHADOW_ENABLED"] = "1"
        env["TOEFL_SHADOW_PROVIDER"] = "claude"
        result = _run([str(INJECTION_SCRIPT), "--limit", "1", "--max-estimated-cost-usd", "1.0",
                        "--i-understand-this-costs-money"], env)
        assert result.returncode == 1
        assert "provider unavailable" in result.stdout

    def test_dry_run_reports_fixture_version(self):
        result = _run([str(INJECTION_SCRIPT), "--limit", "1"], _clean_env())
        assert "fixture v" in result.stdout
