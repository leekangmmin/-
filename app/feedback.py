from __future__ import annotations

import re
from typing import Literal, TypedDict

from app.grammar import analyze_grammar, grammar_analysis_text
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

    return improved, note


def build_feedback(
    essay_text: str, prompt_type: str, total_score: float
) -> FeedbackPayload:
    metrics: EssayMetrics = analyze_essay(essay_text)
    planning_floor = 80 if prompt_type == "email" else 100
    grammar = analyze_grammar(grammar_analysis_text(essay_text, prompt_type))

    strengths: list[str] = []
    weaknesses: list[str] = []
    action_plan: list[str] = []

    if metrics.word_count >= planning_floor:
        strengths.append("아이디어를 전개할 수 있는 권장 연습 분량을 확보했습니다.")
    else:
        weaknesses.append("현재 답안은 전개를 보여 줄 공간이 다소 제한적입니다.")
        action_plan.append(
            "단어 수를 채우기 위한 문장 대신, 가장 중요한 주장 하나에 이유나 구체적 세부 정보를 보태세요."
        )

    if metrics.sentence_count >= 4:
        strengths.append("여러 문장에 걸쳐 핵심 아이디어를 발전시키고 있습니다.")
    else:
        weaknesses.append("핵심 아이디어의 설명이 짧아 수행 정도를 판단하기 어렵습니다.")
        action_plan.append("입장이나 목적 뒤에 원인·결과 또는 구체적 상황을 한두 문장 보태세요.")

    if metrics.evidence_hits >= 2:
        strengths.append("이유·예시·결과를 통해 주장을 뒷받침하는 신호가 보입니다.")
    else:
        weaknesses.append("주장을 뒷받침하는 이유나 세부 정보가 제한적입니다.")
        action_plan.append(
            "연결어를 억지로 추가하지 말고, 독자가 납득할 수 있는 이유 또는 사례를 한 가지 구체화하세요."
        )

    if metrics.lexical_diversity >= 0.62:
        strengths.append("답안 길이 영향을 줄인 어휘 다양성 지표가 안정적입니다.")
    else:
        weaknesses.append("가까운 문장 사이에서 일부 표현이 반복될 가능성이 있습니다.")
        action_plan.append("동의어 수를 늘리기보다 반복된 내용어가 가장 정확한 표현인지 먼저 확인하세요.")

    if grammar.total == 0:
        strengths.append("내장 규칙이 확인할 수 있는 명백한 문법 오류가 없습니다.")
    else:
        weaknesses.append(f"검출 가능한 문법·문장부호 문제가 {grammar.total}건 있습니다.")
        action_plan.append("표시된 오류의 실제 문맥을 확인한 뒤, 의미 전달을 방해하는 항목부터 수정하세요.")

    if not action_plan:
        action_plan.append("현재 구조를 유지하면서 근거 문장을 더 구체화해 1단계 상향을 노리세요.")

    sentence_edits: list[SentenceEdit] = []
    for sentence in _split_sentences(essay_text)[:3]:
        improved, note = _improve_sentence(sentence)
        if improved != sentence:
            sentence_edits.append(
                SentenceEdit(original=sentence, improved=improved, note=note)
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

    confidence = "medium"
    if metrics.word_count < planning_floor or grammar.total >= 6:
        confidence = "low"

    return {
        "strengths": strengths[:4],
        "weaknesses": weaknesses[:5],
        "action_plan": action_plan[:5],
        "sentence_edits": sentence_edits,
        "upgraded_sample_paragraph": upgraded_sample,
        "confidence": confidence,
    }
