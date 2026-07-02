"""채점 엔진 테스트 — 순위 보존, 결정론, 상한 캡."""

from app.scorer import RUBRIC_VERSION, SCORING_ENGINE_VERSION, grammar_cap_status, score_essay
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

    def test_high_quality_reaches_upper_band(self):
        _, high = score_essay(DISCUSSION_HIGH, "academic_discussion")
        # 내부 0-5 스케일 3.5 = 밴드 4.5 이상이어야 한다
        assert high >= 3.5

    def test_low_quality_stays_low(self):
        _, low = score_essay(DISCUSSION_LOW, "academic_discussion")
        assert low <= 1.5


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
