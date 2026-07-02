"""유형별 평가 스키마 테스트."""

import json

import httpx
import pytest

from app.claude_provider import ClaudeScoringProvider
from app.scoring_provider import ScoringInput
from app.shadow_config import ShadowConfig
from app.task_schemas import (
    DISCUSSION_DIMENSIONS,
    EMAIL_DIMENSIONS,
    dimension_ids_for,
    dimension_scoring_instructions,
    requirement_extraction_instructions,
)


class TestDimensionSchemas:
    def test_email_dimensions_are_distinct_from_discussion(self):
        assert set(EMAIL_DIMENSIONS) != set(DISCUSSION_DIMENSIONS)

    def test_email_has_tone_and_register(self):
        assert "tone_and_register" in EMAIL_DIMENSIONS

    def test_discussion_has_engagement_and_distortion_checks(self):
        assert "engagement_with_other_views" in DISCUSSION_DIMENSIONS
        assert "distortion_of_other_views" in DISCUSSION_DIMENSIONS

    def test_dimension_ids_for_unsupported_type_raises(self):
        with pytest.raises(ValueError):
            dimension_ids_for("build_a_sentence")

    def test_requirement_instructions_differ_by_type(self):
        email_text = requirement_extraction_instructions("email")
        discussion_text = requirement_extraction_instructions("academic_discussion")
        assert email_text != discussion_text
        assert "recipient_role" in email_text or "수신자" in email_text
        assert "position" in discussion_text or "입장" in discussion_text


@pytest.fixture()
def cfg() -> ShadowConfig:
    return ShadowConfig(
        enabled=True, provider="claude", anthropic_api_key="test-key",
        model="claude-3-5-sonnet-latest", timeout_seconds=5.0, max_retries=1,
    )


class TestProviderUsesTaskSpecificPrompts:
    def test_email_task_type_gets_email_instructions_in_system_prompt(self, cfg):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            captured["system"] = body["system"]
            return httpx.Response(200, json={"content": [{"type": "text", "text": json.dumps({"is_scorable": True, "reason_codes": [], "warnings": [], "requirements": [], "main_claims": [], "off_topic_risk": False, "template_risk": False})}]})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        provider = ClaudeScoringProvider(cfg, client=client)
        provider.analyze_input(ScoringInput("Dear professor, I am writing to request an extension.", "", "email"))
        assert "writer_role" in captured["system"] or "작성자 역할" in captured["system"]

    def test_discussion_task_type_gets_discussion_instructions(self, cfg):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            captured["system"] = body["system"]
            return httpx.Response(200, json={"content": [{"type": "text", "text": json.dumps({"dimensions": [], "overall_draft_score": 0})}]})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        provider = ClaudeScoringProvider(cfg, client=client)
        from app.scoring_provider import InputAnalysis

        provider.score_dimensions(
            ScoringInput("I agree with this position because...", "", "academic_discussion"),
            InputAnalysis(),
        )
        assert "position" in captured["system"]
        assert "new_contribution" in captured["system"]
