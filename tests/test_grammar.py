"""문법 신호 모듈 회귀 테스트 — 오탐 방지가 핵심이다."""

from app.grammar import analyze_grammar, count_article_mismatch, find_comma_splices, grammar_analysis_text


class TestNoFalsePositives:
    """올바른 영어는 오류로 계산되면 안 된다 (v1 엔진의 P0 버그 회귀 방지)."""

    def test_correct_an_before_vowel(self):
        assert count_article_mismatch("She gave an example and ate an apple.") == 0

    def test_correct_a_before_consonant(self):
        assert count_article_mismatch("He wrote a book about a university.") == 0

    def test_an_before_silent_h(self):
        assert count_article_mismatch("It took an hour to give an honest answer.") == 0

    def test_i_was_is_correct(self):
        sig = analyze_grammar("I was tired yesterday, so I went home early.")
        assert sig.tense == 0

    def test_subjunctive_it_were(self):
        sig = analyze_grammar("If it were possible, I would join the program.")
        assert sig.tense == 0

    def test_compared_with_is_correct(self):
        sig = analyze_grammar("Compared with last year, the results improved.")
        assert sig.preposition == 0

    def test_relative_clause_that_have(self):
        sig = analyze_grammar("Students that have completed the course perform well.")
        assert sig.subject_verb == 0

    def test_dependent_clause_comma_is_not_splice(self):
        assert find_comma_splices(["When I was young, I joined a club."]) == 0
        assert find_comma_splices(["Because they practiced daily, they improved quickly."]) == 0

    def test_coordinated_clause_is_not_splice(self):
        assert find_comma_splices(["I studied hard, and I passed the exam."]) == 0

    def test_semicolon_transition_is_not_comma_splice(self):
        assert find_comma_splices([
            "I booked a ticket; however, I could not find the schedule."
        ]) == 0

    def test_email_salutation_and_signature_are_not_fragments(self):
        email = """To whom it may concern,

I am writing to request the event schedule. Thank you very much for your assistance. I look forward to your reply.

Kind regards,
Taylor"""
        body = grammar_analysis_text(email, "email")
        assert "To whom it may concern" not in body
        assert "Kind regards" not in body
        assert analyze_grammar(body).total == 0

    def test_abbreviations_not_punctuation_error(self):
        sig = analyze_grammar("The U.S. economy grew, e.g. in the tech sector.")
        assert sig.punctuation == 0

    def test_aux_question_not_agreement_error(self):
        sig = analyze_grammar("Does he have enough time to finish the work?")
        assert sig.subject_verb == 0

    def test_clean_paragraph_is_clean(self):
        text = (
            "I believe that collaboration improves learning outcomes. "
            "For example, when students review each other's drafts, they "
            "identify unclear arguments early. Therefore, I support the proposal."
        )
        assert analyze_grammar(text).total == 0


class TestTruePositives:
    """실제 오류는 잡아야 한다."""

    def test_a_before_vowel_sound(self):
        assert count_article_mismatch("She ate a apple.") == 1

    def test_an_before_consonant_sound(self):
        assert count_article_mismatch("He read an book.") == 1

    def test_they_was(self):
        assert analyze_grammar("They was happy about the news.").tense == 1

    def test_he_dont(self):
        assert analyze_grammar("He don't like the class.").subject_verb >= 1

    def test_uncountable_article(self):
        assert analyze_grammar("She gave me a information.").article >= 1

    def test_discuss_about(self):
        assert analyze_grammar("We should discuss about the plan.").preposition == 1

    def test_there_is_many(self):
        assert analyze_grammar("There is many reasons for this.").subject_verb >= 1

    def test_real_comma_splice(self):
        assert find_comma_splices(["I like the class, it is very interesting."]) == 1

    def test_if_i_was(self):
        assert analyze_grammar("If I was a teacher, I will help students.").style >= 1

    def test_more_better(self):
        assert analyze_grammar("This is more better than before.").style >= 1

    def test_i_am_agree(self):
        assert analyze_grammar("I am agree with this idea.").style >= 1

    def test_severe_breakdown_on_error_dense_text(self):
        text = (
            "I am agree that internship is important. Student have many benefit, "
            "they was learning. He don't know how to work. There is many reasons. "
            "I want discuss about this because peoples needs experience. "
            "A information from internet say that intern get job easy. "
            "If I was a manager, I will hires interns. This is more better choice."
        )
        sig = analyze_grammar(text)
        assert sig.total >= 8
        assert sig.repeated_error


class TestStability:
    def test_deterministic(self):
        text = "Students that have completed an internship report an increased sense of direction."
        first = analyze_grammar(text)
        for _ in range(5):
            again = analyze_grammar(text)
            assert again.as_stats_dict() == first.as_stats_dict()

    def test_empty_text(self):
        sig = analyze_grammar("")
        assert sig.total == 0
        assert not sig.severe_breakdown

    def test_unicode_and_emoji(self):
        sig = analyze_grammar("I like studying 📚 with friends. 우리는 함께 공부한다.")
        assert sig.total >= 0  # 크래시하지 않아야 한다
