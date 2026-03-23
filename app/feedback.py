from __future__ import annotations

import re
from typing import Literal, TypedDict

from app.models import SentenceEdit
from app.scorer import EssayMetrics, analyze_essay


class FeedbackPayload(TypedDict):
    strengths: list[str]
    weaknesses: list[str]
    action_plan: list[str]
    sentence_edits: list[SentenceEdit]
    upgraded_sample_paragraph: str
    confidence: Literal["low", "medium", "high"]


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def _improve_sentence(sentence: str) -> tuple[str, str]:
    improved = sentence
    note = "Clarity and grammar refinement"

    if sentence and sentence[0].islower():
        improved = sentence[0].upper() + sentence[1:]
        note = "Fixed capitalization at sentence start"

    improved = re.sub(r"\bvery\s+", "", improved, flags=re.IGNORECASE)
    improved = re.sub(r"\ba lot of\b", "many", improved, flags=re.IGNORECASE)
    improved = re.sub(r"\bthings\b", "factors", improved, flags=re.IGNORECASE)

    if len(improved.split()) > 32:
        improved = improved.replace(", and", ". In addition," if ", and" in improved else ", and", 1
        )
        note = "Reduced run-on tendency and improved flow"

    return improved, note


def build_feedback(
    essay_text: str, prompt_type: str, total_score: float
) -> FeedbackPayload:
    metrics: EssayMetrics = analyze_essay(essay_text)
    recommended_words = 100 if prompt_type == "email" else 120

    strengths: list[str] = []
    weaknesses: list[str] = []
    action_plan: list[str] = []

    if metrics.word_count >= recommended_words:
        strengths.append("요구 분량을 안정적으로 충족하고 있습니다.")
    else:
        weaknesses.append("분량이 짧아 논리 전개가 충분히 드러나지 않습니다.")
        action_plan.append(
            f"최소 {recommended_words}단어를 넘기도록 핵심 주장 뒤에 이유 2개와 구체 예시 1개를 추가하세요."
        )

    if metrics.paragraph_count >= 3:
        strengths.append("문단 구성이 명확해 읽는 흐름이 안정적입니다.")
    else:
        weaknesses.append("문단 분리가 약해 아이디어 경계가 불분명합니다.")
        action_plan.append("서론-본론-결론 3단 구조로 문단을 분리하세요.")

    if metrics.transition_hits >= 3:
        strengths.append("연결어 사용이 있어 문장 간 논리 연결이 잘 보입니다.")
    else:
        weaknesses.append("연결어가 부족해 문장 간 점프가 발생합니다.")
        action_plan.append(
            "However, Therefore, For example 같은 연결어를 문단당 1개 이상 넣으세요."
        )

    if metrics.lexical_diversity >= 0.42:
        strengths.append("어휘 반복이 과하지 않아 표현 폭이 괜찮습니다.")
    else:
        weaknesses.append("같은 단어 반복이 많아 표현이 단조롭게 느껴집니다.")
        action_plan.append("반복 단어 5개를 동의어로 교체해 어휘 다양성을 높이세요.")

    if metrics.long_sentence_ratio > 0.25:
        weaknesses.append("긴 문장이 많아 문법 오류 가능성과 가독성 저하가 있습니다.")
        action_plan.append("35단어 이상 문장을 둘로 분리해 명확도를 높이세요.")

    if not action_plan:
        action_plan.append("현재 구조를 유지하면서 근거 문장을 더 구체화해 1단계 상향을 노리세요.")

    sentence_edits: list[SentenceEdit] = []
    for sentence in _split_sentences(essay_text)[:3]:
        improved, note = _improve_sentence(sentence)
        if improved != sentence:
            sentence_edits.append(
                SentenceEdit(original=sentence, improved=improved, note=note)
            )

    if not sentence_edits:
        sentence_edits.append(
            SentenceEdit(
                original="I think students should use evidence clearly.",
                improved="I argue that students should support each claim with specific evidence.",
                note="Upgrade to a more academic and precise tone",
            )
        )

    if prompt_type == "email":
        upgraded_sample = (
            "Dear Professor Smith, I am writing to request an extension for the upcoming "
            "assignment due to a family emergency. I have been making consistent progress "
            "on the project; however, the unexpected situation has limited my available time. "
            "I would greatly appreciate the opportunity to submit the work by this Friday. "
            "Please let me know if this is possible. Thank you for your understanding and "
            "consideration. Sincerely, [Your Name]"
        )
    else:
        upgraded_sample = (
            "I agree that schools should invest more in collaborative projects because "
            "they improve both communication and problem-solving. For example, when "
            "students divide roles and synthesize ideas, they practice negotiation and "
            "evidence-based reasoning. In addition, team tasks mirror real workplace "
            "demands, so students gain transferable skills before graduation."
        )

    confidence = "high" if 2.5 <= total_score <= 4.5 else "medium"
    if metrics.word_count < recommended_words:
        confidence = "low"

    return {
        "strengths": strengths[:4],
        "weaknesses": weaknesses[:5],
        "action_plan": action_plan[:5],
        "sentence_edits": sentence_edits,
        "upgraded_sample_paragraph": upgraded_sample,
        "confidence": confidence,
    }
