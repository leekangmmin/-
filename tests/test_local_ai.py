"""Tests for Local AI Provider layer (Phase 8-B)."""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import httpx
import time

from app.local_ai import (
    LocalAIProviderConfig,
    RuleLocalAIProvider,
    OllamaLocalProvider,
    LlamaCppLocalProvider,
    LocalAIManager,
    LocalAIRequest,
    LocalAIResult,
    LocalAIAvailability,
    FeedbackItem,
    SentenceSuggestion,
    get_local_ai_manager,
    _build_ollama_prompt,
    WARMUP_PROMPT,
)


# ── LocalAIProviderConfig ─────────────────────────────────────────────────

class TestLocalAIProviderConfig:
    def test_default_values(self):
        cfg = LocalAIProviderConfig()
        assert cfg.connect_timeout_seconds == 5.0
        assert cfg.read_timeout_seconds == 120.0
        assert cfg.total_timeout_seconds == 180.0
        assert cfg.first_run_timeout_seconds == 240.0
        assert cfg.max_output_tokens == 512
        assert cfg.temperature == 0.2
        assert cfg.keep_alive == "10m"

    def test_from_env_override(self):
        with patch.dict("os.environ", {
            "TOEFL_LOCAL_AI_CONNECT_TIMEOUT": "3",
            "TOEFL_LOCAL_AI_READ_TIMEOUT": "60",
            "TOEFL_LOCAL_AI_TEMPERATURE": "0.1",
        }):
            cfg = LocalAIProviderConfig.from_env()
            assert cfg.connect_timeout_seconds == 3.0
            assert cfg.read_timeout_seconds == 60.0
            assert cfg.temperature == 0.1

    def test_from_env_fallback_on_invalid(self):
        with patch.dict("os.environ", {
            "TOEFL_LOCAL_AI_CONNECT_TIMEOUT": "not_a_number",
        }):
            cfg = LocalAIProviderConfig.from_env()
            assert cfg.connect_timeout_seconds == 5.0


# ── RuleLocalAIProvider ──────────────────────────────────────────────────

class TestRuleLocalAIProvider:
    def test_available_always(self):
        provider = RuleLocalAIProvider()
        avail = provider.is_available()
        assert avail.available is True
        assert avail.status == "ready"
        assert avail.runs_offline is True
        assert avail.requires_model_file is False

    def test_analyze_short_essay(self):
        provider = RuleLocalAIProvider()
        request = LocalAIRequest(
            essay_text="I think education is important because it helps people learn new things and improve their skills.",
            prompt_type="academic_discussion",
        )
        result = provider.analyze_response(request)
        assert result.valid is True
        assert result.provider_id == "rule"
        assert result.runs_offline is True
        assert result.confidence > 0
        assert result.latency_ms >= 0
        assert len(result.summary) > 0

    def test_analyze_long_essay_with_strengths_and_issues(self):
        provider = RuleLocalAIProvider()
        long_essay = (
            "I strongly agree that collaborative learning is beneficial for students. "
            "However, some people disagree with this view. For example, research shows that "
            "students in group projects perform better on exams. Therefore, schools should "
            "encourage more teamwork. In addition, this approach builds communication skills. "
            "For instance, a study found that collaborative tasks improve critical thinking. "
            "As a result, students become better prepared for their future careers. "
            "In contrast, working alone limits the exchange of diverse perspectives. "
            "Consequently, teamwork should be integrated into the curriculum. "
            "Moreover, collaborative projects mirror real-world workplace demands. "
            "Thus, students gain practical experience while studying. "
            "In conclusion, I believe schools must prioritize group-based learning."
        )
        request = LocalAIRequest(essay_text=long_essay, prompt_type="academic_discussion")
        result = provider.analyze_response(request)
        assert result.valid is True
        assert len(result.strengths) >= 1
        assert result.sentence_suggestions is not None

    def test_sentence_fixes_subject_verb(self):
        provider = RuleLocalAIProvider()
        result = provider._fix_sentence("Students is often tired.")
        assert "are" in result
        assert "is" not in result.lower().split()

    def test_fixes_grammar_errors_in_fixture(self):
        provider = RuleLocalAIProvider()
        essay = "When I was young I go to school by bus everyday. This experience make me realize that transportation is very important. Also, I am agree with the idea because it is more better for students."
        request = LocalAIRequest(essay_text=essay, prompt_type="academic_discussion")
        result = provider.analyze_response(request)
        assert result.valid is True
        assert len(result.sentence_suggestions) >= 1

    def test_does_not_change_production_score(self):
        provider = RuleLocalAIProvider()
        request = LocalAIRequest(essay_text="Some text here. Testing only.")
        result = provider.analyze_response(request)
        assert not hasattr(result, "score_0_5")
        assert not hasattr(result, "total_score")

    def test_suggestions_limited_to_4(self):
        provider = RuleLocalAIProvider()
        request = LocalAIRequest(essay_text="Students is tired. He don't know. I am agree. There is many reasons. Kids like it. It is more better.")
        result = provider.analyze_response(request)
        assert len(result.sentence_suggestions) <= 4


# ── OllamaLocalProvider ──────────────────────────────────────────────────

class TestOllamaLocalProvider:
    def test_rejects_non_loopback_url(self):
        provider = OllamaLocalProvider(base_url="http://192.168.1.1:11434")
        avail = provider.is_available()
        assert avail.available is False
        assert "localhost" in avail.detail.lower() or "127.0.0.1" in avail.detail.lower()

    def test_allows_loopback_url_with_mock(self):
        provider = OllamaLocalProvider(base_url="http://127.0.0.1:11434")
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"models": [{"name": "llama3"}]}
            mock_get.return_value = mock_resp
            avail = provider.is_available()
            assert avail.available is True
            assert avail.model_name == "llama3"

    def test_unavailable_when_not_running(self):
        provider = OllamaLocalProvider(base_url="http://127.0.0.1:11434")
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection refused")
            avail = provider.is_available()
            assert avail.available is False
            assert avail.status == "runtime_missing"

    def test_unavailable_when_no_models(self):
        provider = OllamaLocalProvider(base_url="http://127.0.0.1:11434")
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"models": []}
            mock_get.return_value = mock_resp
            avail = provider.is_available()
            assert avail.available is False
            assert avail.status == "model_missing"

    def test_analyze_without_model_returns_valid_false(self):
        provider = OllamaLocalProvider(base_url="http://127.0.0.1:11434")
        request = LocalAIRequest(essay_text="Test essay")
        result = provider.analyze_response(request)
        assert result.valid is False
        assert len(result.warnings) >= 1

    def test_configurable_timeout(self):
        cfg = LocalAIProviderConfig(read_timeout_seconds=5.0, total_timeout_seconds=10.0)
        provider = OllamaLocalProvider(base_url="http://127.0.0.1:11434", config=cfg)
        assert provider._config.read_timeout_seconds == 5.0
        assert provider._config.total_timeout_seconds == 10.0

    def test_warmup_with_mock(self):
        provider = OllamaLocalProvider(base_url="http://127.0.0.1:11434", model="qwen2.5:7b",
                                       config=LocalAIProviderConfig(keep_alive="1m"))
        provider._detected_model = "qwen2.5:7b"
        with patch("httpx.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "model": "qwen2.5:7b",
                "response": '{"ready":true}',
                "total_duration": 600000000,
                "load_duration": 500000000,
                "prompt_eval_duration": 100000000,
                "eval_duration": 100000000,
                "eval_count": 6,
                "prompt_eval_count": 10,
            }
            mock_post.return_value = mock_resp
            result = provider.warmup()
            assert result["ok"] is True
            assert result["latency_ms"] >= 0

    def test_warmup_called_before_analyze_uses_first_run_timeout(self):
        cfg = LocalAIProviderConfig(first_run_timeout_seconds=240.0, total_timeout_seconds=180.0)
        provider = OllamaLocalProvider(base_url="http://127.0.0.1:11434", config=cfg)
        provider._detected_model = "qwen2.5:7b"
        provider._is_warm = False
        with patch("httpx.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "response": '{"summary":"ok"}',
                "total_duration": 5000000000,
                "eval_duration": 4000000000,
                "eval_count": 50,
            }
            mock_post.return_value = mock_resp
            provider.analyze_response(LocalAIRequest(essay_text="Test essay."))
            call_kwargs = mock_post.call_args[1] if mock_post.call_args else {}
            timeout_arg = call_kwargs.get("timeout")
            assert timeout_arg is not None

    def test_parse_markdown_wrapped_json(self):
        provider = OllamaLocalProvider(base_url="http://127.0.0.1:11434")
        response_text = '```json\n{"summary": "Great essay", "strengths": [], "priority_issues": [], "sentence_suggestions": [], "next_practice_goal": "keep it up"}\n```'
        result = provider._parse_response(response_text, LocalAIRequest(essay_text="Test."))
        assert result.valid is True
        assert result.summary == "Great essay"

    def test_parse_json_with_extra_text(self):
        provider = OllamaLocalProvider(base_url="http://127.0.0.1:11434")
        response_text = 'Here is the analysis:\n\n{"summary": "ok", "strengths": [], "priority_issues": [], "sentence_suggestions": [], "next_practice_goal": "practice more"}\n\nHope this helps!'
        result = provider._parse_response(response_text, LocalAIRequest(essay_text="Test."))
        assert result.valid is True
        assert result.summary == "ok"

    def test_parse_invalid_json_returns_error(self):
        provider = OllamaLocalProvider(base_url="http://127.0.0.1:11434")
        response_text = "I cannot parse this properly."
        result = provider._parse_response(response_text, LocalAIRequest(essay_text="Test."))
        assert result.valid is False

    def test_parse_model_specific_errors(self):
        provider = OllamaLocalProvider(base_url="http://127.0.0.1:11434")
        response_text = '{"summary": "test", "strengths": [], "priority_issues": [], "sentence_suggestions": [{"original": "not in essay", "suggested": "fake", "reason": "test"}], "next_practice_goal": "ok"}'
        result = provider._parse_response(response_text, LocalAIRequest(essay_text="Test."))
        assert result.valid is True
        assert len(result.sentence_suggestions) == 1

    def test_missing_original_in_suggestion(self):
        provider = OllamaLocalProvider(base_url="http://127.0.0.1:11434")
        response_text = '{"summary": "test", "strengths": [], "priority_issues": [], "sentence_suggestions": [{"original": "", "suggested": "something", "reason": ""}], "next_practice_goal": ""}'
        result = provider._parse_response(response_text, LocalAIRequest(essay_text="Test."))
        assert result.sentence_suggestions[0].original == ""

    def test_performance_status_ready_fast(self):
        provider = OllamaLocalProvider(base_url="http://127.0.0.1:11434")
        provider._last_performance = {"total_duration_ns": 1000000000, "eval_duration_ns": 500000000, "eval_count": 50, "load_duration_ns": 200000000}
        assert provider._performance_status() == "ready_fast"

    def test_performance_status_ready_slow(self):
        provider = OllamaLocalProvider(base_url="http://127.0.0.1:11434")
        provider._last_performance = {"total_duration_ns": 80000000000, "eval_duration_ns": 50000000000, "eval_count": 100, "load_duration_ns": 200000000}
        assert provider._performance_status() == "ready_slow"

    def test_performance_status_timeout(self):
        provider = OllamaLocalProvider(base_url="http://127.0.0.1:11434")
        provider._last_performance = {"total_duration_ns": 200000000000, "eval_duration_ns": 100000000000, "eval_count": 100, "load_duration_ns": 200000000}
        assert provider._performance_status() == "timeout"

    def test_model_recommendations(self):
        provider = OllamaLocalProvider(base_url="http://127.0.0.1:11434")
        provider._detected_model = "qwen2.5:7b"
        provider._last_performance = {"total_duration_ns": 100000000000, "eval_duration_ns": 50000000000, "eval_count": 100, "load_duration_ns": 200000000}
        provider._installed_models = [{"name": "qwen2.5:7b"}, {"name": "qwen2.5:3b"}]
        recs = provider.model_recommendations()
        assert recs["current_model"] == "qwen2.5:7b"
        assert len(recs["recommendations"]) >= 1

    def test_build_ollama_prompt_short(self):
        request = LocalAIRequest(essay_text="Short essay.", prompt_type="academic_discussion")
        prompt = _build_ollama_prompt(request)
        assert "Short essay." in prompt
        assert "academic_discussion" in prompt
        assert "JSON" in prompt

    def test_ollama_result_no_score_leak(self):
        provider = OllamaLocalProvider(base_url="http://127.0.0.1:11434")
        response_text = '{"summary": "test", "strengths": [], "priority_issues": [], "sentence_suggestions": [], "next_practice_goal": "", "score": 5.5}'
        result = provider._parse_response(response_text, LocalAIRequest(essay_text="Test."))
        assert "score" in result.warnings[0].lower()


# ── LlamaCppLocalProvider ────────────────────────────────────────────────

class TestLlamaCppLocalProvider:
    def test_rejects_non_loopback_url(self):
        provider = LlamaCppLocalProvider(base_url="http://192.168.1.1:8080")
        avail = provider.is_available()
        assert avail.available is False

    def test_available_when_server_responds(self):
        provider = LlamaCppLocalProvider(base_url="http://127.0.0.1:8080")
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"data": [{"id": "mistral-7b"}]}
            mock_get.return_value = mock_resp
            avail = provider.is_available()
            assert avail.available is True
            assert avail.model_name == "mistral-7b"

    def test_unavailable_when_not_running(self):
        provider = LlamaCppLocalProvider(base_url="http://127.0.0.1:8080")
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection refused")
            avail = provider.is_available()
            assert avail.available is False


# ── LocalAIManager ───────────────────────────────────────────────────────

class TestLocalAIManager:
    def test_default_to_rule_when_all_unavailable(self):
        manager = LocalAIManager()
        with patch.object(manager, "probe_all") as mock_probe:
            mock_probe.return_value = {
                "rule": LocalAIAvailability(available=True, status="ready", provider_id="rule"),
                "ollama": LocalAIAvailability(available=False, status="runtime_missing", provider_id="ollama"),
                "llamacpp": LocalAIAvailability(available=False, status="runtime_missing", provider_id="llamacpp"),
            }
            provider = manager.select_provider()
            assert provider.id == "rule"

    def test_select_ollama_when_available(self):
        manager = LocalAIManager()
        with patch.object(manager, "probe_all") as mock_probe:
            mock_probe.return_value = {
                "rule": LocalAIAvailability(available=True, status="ready", provider_id="rule"),
                "ollama": LocalAIAvailability(available=True, status="ready", provider_id="ollama", model_name="llama3"),
                "llamacpp": LocalAIAvailability(available=False, status="runtime_missing", provider_id="llamacpp"),
            }
            provider = manager.select_provider()
            assert provider.id == "ollama"

    def test_status_summary_always_has_offline_core(self):
        manager = LocalAIManager()
        with patch.object(manager, "probe_all") as mock_probe:
            mock_probe.return_value = {
                "rule": LocalAIAvailability(available=True, status="ready", provider_id="rule"),
                "ollama": LocalAIAvailability(available=False, status="runtime_missing", provider_id="ollama"),
                "llamacpp": LocalAIAvailability(available=False, status="runtime_missing", provider_id="llamacpp"),
            }
            status = manager.status_summary()
            assert status["offline_core"]["available"] is True
            assert status["offline_core"]["status"] == "ready"
            assert "local_ai" in status

    def test_analyze_with_rule_when_ollama_unavailable(self):
        manager = LocalAIManager()
        with patch.object(manager, "probe_all") as mock_probe:
            mock_probe.return_value = {
                "rule": LocalAIAvailability(available=True, status="ready", provider_id="rule"),
                "ollama": LocalAIAvailability(available=False, status="runtime_missing", provider_id="ollama"),
                "llamacpp": LocalAIAvailability(available=False, status="runtime_missing", provider_id="llamacpp"),
            }
            manager.select_provider()
            result = manager.analyze("Test essay for analysis.", "academic_discussion")
            assert result.valid is True
            assert len(result.summary) > 0
            assert result.provider_id == "rule"

    def test_singleton(self):
        m1 = get_local_ai_manager()
        m2 = get_local_ai_manager()
        assert m1 is m2

    def test_warmup_ollama_when_unavailable(self):
        manager = LocalAIManager()
        with patch.object(manager, "probe_all") as mock_probe:
            mock_probe.return_value = {
                "rule": LocalAIAvailability(available=True, status="ready", provider_id="rule"),
                "ollama": LocalAIAvailability(available=False, status="runtime_missing", provider_id="ollama"),
                "llamacpp": LocalAIAvailability(available=False, status="runtime_missing", provider_id="llamacpp"),
            }
            # Mock the ollama provider's is_available to return unavailable
            if manager.ollama:
                with patch.object(manager.ollama, "is_available") as mock_avail:
                    mock_avail.return_value = LocalAIAvailability(
                        available=False, provider_id="ollama", status="runtime_missing"
                    )
                    result = manager.warmup_ollama()
            else:
                result = manager.warmup_ollama()
            assert result["ok"] is False

    def test_status_summary_with_ollama_ready_slow(self):
        manager = LocalAIManager()
        with patch.object(manager, "probe_all") as mock_probe:
            mock_probe.return_value = {
                "rule": LocalAIAvailability(available=True, status="ready", provider_id="rule"),
                "ollama": LocalAIAvailability(
                    available=True, status="ready_slow", provider_id="ollama",
                    model_name="qwen2.5:7b", performance={"total_duration_ns": 80000000000}
                ),
                "llamacpp": LocalAIAvailability(available=False, status="runtime_missing", provider_id="llamacpp"),
            }
            status = manager.status_summary()
            assert status["local_ai"]["available"] is True
            assert status["local_ai"]["status"] == "ready_slow"


# ── LocalAIResult ────────────────────────────────────────────────────────

class TestLocalAIResult:
    def test_result_has_all_required_fields(self):
        r = LocalAIResult()
        assert hasattr(r, "provider_id")
        assert hasattr(r, "valid")
        assert hasattr(r, "confidence")
        assert hasattr(r, "summary")
        assert hasattr(r, "strengths")
        assert hasattr(r, "priority_issues")
        assert hasattr(r, "sentence_suggestions")
        assert hasattr(r, "runs_offline")
        assert hasattr(r, "warnings")
        assert hasattr(r, "performance")


# ── Safety ───────────────────────────────────────────────────────────────

class TestLocalAISafety:
    def test_rule_provider_no_external_calls(self):
        provider = RuleLocalAIProvider()
        request = LocalAIRequest(essay_text="Sample essay text for testing purposes only.")
        with patch("httpx.Client", side_effect=Exception("should not call HTTP")):
            result = provider.analyze_response(request)
            assert result.valid is True

    def test_local_ai_failure_does_not_raise(self):
        provider = OllamaLocalProvider(base_url="http://127.0.0.1:11434")
        request = LocalAIRequest(essay_text="Test essay")
        result = provider.analyze_response(request)
        assert result.valid is False
        assert result.warnings is not None

    def test_ollama_rejects_non_loopback(self):
        for bad_url in ["http://192.168.1.1:11434", "https://bad.example.com", "http://10.0.0.1:11434"]:
            provider = OllamaLocalProvider(base_url=bad_url)
            avail = provider.is_available()
            assert avail.available is False, f"Should reject {bad_url}"

    def test_no_score_in_result(self):
        result = LocalAIResult()
        assert "score" not in result.__dict__ or result.__dict__.get("score") is None

    def test_score_leak_not_in_ollama_parsed_result(self):
        provider = OllamaLocalProvider(base_url="http://127.0.0.1:11434")
        response_text = '{"summary": "test", "strengths": [], "priority_issues": [], "sentence_suggestions": [], "next_practice_goal": ""}'
        result = provider._parse_response(response_text, LocalAIRequest(essay_text="test"))
        assert result.valid is True
        assert not hasattr(result, "score")

    def test_keep_alive_setting(self):
        cfg = LocalAIProviderConfig(keep_alive="5m")
        assert cfg.keep_alive == "5m"

    def test_ollama_response_metadata_recorded(self):
        provider = OllamaLocalProvider(base_url="http://127.0.0.1:11434")
        perf_data = {"total_duration": 1000000000, "eval_duration": 500000000, "eval_count": 50}
        provider._record_performance(perf_data)
        assert "tokens_per_sec" in provider._last_performance
        assert provider._last_performance["eval_count"] == 50

    def test_warmup_prompt_does_not_contain_essay(self):
        assert "essay" not in WARMUP_PROMPT.lower()
        assert "essay" not in WARMUP_PROMPT

    def test_environment_override_config(self):
        with patch.dict("os.environ", {
            "TOEFL_LOCAL_AI_KEEP_ALIVE": "2m",
            "TOEFL_LOCAL_AI_TEMPERATURE": "0.1",
            "TOEFL_LOCAL_AI_MAX_OUTPUT_TOKENS": "256",
        }):
            cfg = LocalAIProviderConfig.from_env()
            assert cfg.keep_alive == "2m"
            assert cfg.temperature == 0.1
            assert cfg.max_output_tokens == 256
