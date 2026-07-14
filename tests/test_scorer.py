"""채점 엔진 테스트 — 순위 보존, 결정론, 상한 캡."""

from app.scorer import RUBRIC_VERSION, SCORING_ENGINE_VERSION, grammar_cap_status, score_essay
from app.advanced import bilingual_summary
from tests.fixtures import (
    DISCUSSION_HIGH,
    DISCUSSION_LOW,
    DISCUSSION_MID,
    EMAIL_HIGH,
    EMAIL_LOW,
)


class TestRanking:
    """품질이 명확히 다른 답안의 순위는 뒤집히면 안 된다."""

    def test_discussion_high_beats_mid(self):
        _, high = score_essay(DISCUSSION_HIGH, "academic_discussion")
        _, mid = score_essay(DISCUSSION_MID, "academic_discussion")
        assert high > mid

    def test_discussion_mid_beats_low(self):
        _, mid = score_essay(DISCUSSION_MID, "academic_discussion")
        _, low = score_essay(DISCUSSION_LOW, "academic_discussion")
        assert mid > low

    def test_email_high_beats_low(self):
        _, high = score_essay(EMAIL_HIGH, "email")
        _, low = score_essay(EMAIL_LOW, "email")
        assert high > low

    def test_high_quality_gratitude_email_reaches_upper_band_without_request(self):
        synthetic = """Dear Museum Director,

I am writing to express my sincere gratitude for the thoughtful assistance during our school visit. We especially appreciated the accessible tour materials and the extra time your guide spent answering our questions.

After the tour, one student noticed that her notebook was missing. Although the building was about to close, your staff searched the classroom until they found it. Their patience made the student feel supported and allowed our group to leave with a very positive impression.

Thank you once again for your professionalism and generous hospitality. We wish the museum continued success.

Sincerely,
Jordan Lee"""
        _, score = score_essay(synthetic, "email")
        assert score >= 4.0  # displayed practice band >= 5.0

    def test_high_quality_reaches_upper_band(self):
        _, high = score_essay(DISCUSSION_HIGH, "academic_discussion")
        # 내부 0-5 스케일 3.5 = 밴드 4.5 이상이어야 한다
        assert high >= 3.5

    def test_low_quality_stays_low(self):
        _, low = score_essay(DISCUSSION_LOW, "academic_discussion")
        assert low <= 1.5

    def test_expert_calibrated_complete_email_can_reach_five(self):
        # Synthetic regression fixture: it encodes only abstract moves observed
        # in expert-reviewed work and contains no supplied model-answer text.
        synthetic = """Dear Events Coordinator,

I am writing to ask for details about next month's public science lecture. I registered yesterday because the topic connects directly to biology research for my class. However, the confirmation page did not identify the guest speaker or describe the experiments that will be presented. My teacher requires a detailed summary after the visit, so I hope to review the background material in advance.

Could you please send me the lecture outline? In addition, I would be grateful if you could confirm the starting time and let me know whether student visitors may bring a classmate. This information will help me prepare useful questions before the event.

Thank you very much for your time and assistance. I look forward to your reply.

Best regards,
Taylor"""
        _, score = score_essay(synthetic, "email")
        assert score == 5.0

    def test_expert_calibrated_discussion_with_two_views_can_reach_five(self):
        synthetic = """I firmly believe that high school students gain more from community service projects because older learners can connect practical work with academic knowledge and long-term goals.

I agree with Daniel's point that shared projects teach responsibility. As a result, students learn to divide complex duties and evaluate one another's ideas. In addition, they can practice explaining decisions to people outside their usual classroom.

Maya raises a fair concern that younger children need chances to cooperate. However, older students also face demanding choices about college and employment. For example, a team that designs a neighborhood recycling campaign must research local needs, negotiate a realistic plan, and present measurable results to residents. Therefore, the activity develops both critical thinking and professional communication.

For these reasons, I strongly believe older students receive the greater educational benefit."""
        _, score = score_essay(synthetic, "academic_discussion")
        assert score == 5.0


class TestDeterminism:
    def test_repeated_scoring_identical(self):
        scores = [score_essay(DISCUSSION_MID, "academic_discussion")[1] for _ in range(5)]
        assert len(set(scores)) == 1

    def test_score_in_valid_range(self):
        for essay, ptype in [
            (DISCUSSION_HIGH, "academic_discussion"),
            (DISCUSSION_LOW, "academic_discussion"),
            (EMAIL_HIGH, "email"),
            (EMAIL_LOW, "email"),
        ]:
            dims, total = score_essay(essay, ptype)
            assert 0.0 <= total <= 5.0
            for d in dims:
                assert 0.0 <= d.score <= 5.0


def test_five_point_summary_does_not_invent_a_weakness():
    summary = bilingual_summary(5.0, 5.0, [], prompt_fit_evaluated=False)
    assert "현재의 과제 충족도" in summary["summary_ko"]
    assert "근거를 더" not in summary["summary_ko"]


class TestGrammarCap:
    def test_no_cap_on_clean_essay(self):
        cap = grammar_cap_status(DISCUSSION_HIGH)
        assert cap["applied"] is False

    def test_cap_on_error_dense_essay(self):
        cap = grammar_cap_status(DISCUSSION_LOW)
        assert cap["applied"] is True


class TestVersioning:
    def test_versions_exist(self):
        assert SCORING_ENGINE_VERSION
        assert RUBRIC_VERSION
        assert SCORING_ENGINE_VERSION == "2.3.0"
