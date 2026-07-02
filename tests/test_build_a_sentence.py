"""Build a Sentence 결정론적 채점 엔진 테스트.

목표: 자체 제작 문항 세트에서 정확도 100%(공식 정답이 있는 문제 세트의
목표치, 마스터 스펙 14.1). 여기서는 우리가 만든 합성 문항이므로 "실제 시험
정확도"가 아니라 "엔진 로직이 우리가 의도한 대로 동작하는지"를 검증한다.
"""

from app.build_a_sentence_engine import normalize, score_submission
from tests.build_a_sentence_fixtures import ITEM_CASE_SENSITIVE, ITEM_CONTRACTION, ITEM_SIMPLE


class TestExactMatch:
    def test_exact_primary_answer(self):
        result = score_submission(ITEM_SIMPLE, "The students finished their homework before dinner.")
        assert result.is_correct is True
        assert result.match_type == "exact"

    def test_case_insensitive_by_default(self):
        result = score_submission(ITEM_SIMPLE, "the students finished their homework before dinner")
        assert result.is_correct is True
        assert result.match_type == "exact"

    def test_terminal_punctuation_ignored(self):
        result = score_submission(ITEM_SIMPLE, "The students finished their homework before dinner")
        assert result.is_correct is True


class TestAllowedVariants:
    def test_alternative_word_order_accepted(self):
        result = score_submission(ITEM_SIMPLE, "Before dinner, the students finished their homework.")
        assert result.is_correct is True
        assert result.match_type == "allowed_variant"

    def test_contraction_variant_accepted(self):
        result = score_submission(ITEM_CONTRACTION, "She isn't ready yet.")
        assert result.is_correct is True
        assert result.match_type == "allowed_variant"

    def test_expanded_form_also_correct(self):
        result = score_submission(ITEM_CONTRACTION, "She is not ready yet.")
        assert result.is_correct is True
        assert result.match_type == "exact"


class TestStructuralPartial:
    def test_all_components_present_but_wrong_form_not_marked_correct(self):
        # 모든 구성요소는 들어있지만 정답 목록에 없는 표현 — 정답 처리하면 안 됨
        result = score_submission(ITEM_SIMPLE, "Their homework the students finished before dinner.")
        assert result.is_correct is False
        assert result.match_type == "structural_partial"
        assert result.missing_fragments == []

    def test_missing_component_reported(self):
        result = score_submission(ITEM_SIMPLE, "The students finished their homework.")
        assert result.is_correct is False
        assert "before dinner" in result.missing_fragments


class TestNoMatch:
    def test_completely_wrong_answer(self):
        result = score_submission(ITEM_SIMPLE, "I like pizza on weekends.")
        assert result.is_correct is False
        assert result.match_type == "none"

    def test_engine_never_guesses_generously(self):
        """공식/허용 정답 목록에 없으면, 그럴듯해 보여도 정답 처리하지 않는다."""
        result = score_submission(ITEM_SIMPLE, "The student finished his homework before dinner.")
        # "student"(단수)+"his"로 원래 구성요소와 다름 — extra_tokens에 잡혀야 함
        assert result.is_correct is False


class TestCaseSensitivePolicy:
    def test_case_sensitive_item_rejects_lowercase_proper_noun(self):
        result = score_submission(ITEM_CASE_SENSITIVE, "professor kim will announce the results tomorrow.")
        assert result.is_correct is False

    def test_case_sensitive_item_accepts_correct_case(self):
        result = score_submission(ITEM_CASE_SENSITIVE, "Professor Kim will announce the results tomorrow.")
        assert result.is_correct is True


class TestNormalization:
    def test_normalize_is_deterministic(self):
        text = "The Students Finished Their Homework Before Dinner."
        assert normalize(text, ITEM_SIMPLE) == normalize(text, ITEM_SIMPLE)

    def test_whitespace_collapsed(self):
        result = score_submission(ITEM_SIMPLE, "The   students finished   their homework before dinner.")
        assert result.is_correct is True


class TestProvenanceRequired:
    def test_items_have_synthetic_provenance_not_official(self):
        for item in [ITEM_SIMPLE, ITEM_CONTRACTION, ITEM_CASE_SENSITIVE]:
            assert item.provenance.source_type == "synthetic"
            assert item.provenance.is_official is False
