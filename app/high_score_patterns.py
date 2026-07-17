"""Abstract writing-move detection; contains no corpus sentences or model answers."""

from __future__ import annotations

import re
from dataclasses import dataclass


HIGH_SCORE_MOVES = {
    "academic_discussion": [
        "stance", "reason", "specific_example", "explanation", "other_view", "prompt_connection", "reinforcement"
    ],
    "email": ["greeting", "purpose", "situation_detail", "polite_request", "second_action", "commitment", "closing"],
}

# Only these moves are broadly necessary to accomplish the task. The remaining
# patterns are optional ways to develop or organize a response; their absence
# must not be presented as a scoring defect.
CORE_MOVES = {
    "academic_discussion": ["stance", "reason"],
    "email": ["purpose", "situation_detail"],
}

MOVE_LABELS_KO = {
    "greeting": "자연스러운 인사", "purpose": "글을 쓰는 목적", "situation_detail": "구체적인 상황 설명",
    "polite_request": "정중하고 직접적인 요청", "second_action": "두 번째 요청 또는 후속 조치",
    "commitment": "협조 의사 또는 감사", "closing": "간단한 맺음말", "stance": "명확한 입장",
    "reason": "주장을 뒷받침하는 이유", "specific_example": "구체적인 예시", "explanation": "예시의 영향 설명",
    "other_view": "다른 학생 의견에 대한 반응", "prompt_connection": "질문과의 연결", "reinforcement": "입장 재강조",
}

_PATTERNS = {
    "email": {
        "greeting": r"^\s*(dear|hello|hi|good (morning|afternoon)|to whom it may concern)\b",
        "purpose": r"\b(i am writing (to|concerning|regarding)|i would like to|i am contacting you)\b",
        "situation_detail": r"\b(unfortunately|because|due to|as|the problem|the issue|specifically)\b",
        "polite_request": r"\b(could you please|would you please|i would be grateful if|i would appreciate it if|please)\b",
        "second_action": r"\b(i would also|also appreciate|in addition|and let me know|as well)\b",
        "commitment": r"\b(i am committed to|thank you(?: very much)? for|grateful for|appreciate your|your understanding)\b",
        "closing": r"\b(sincerely|best regards|kind regards|regards|yours truly)\b",
    },
    "academic_discussion": {
        "stance": r"\b(i (firmly |strongly )?(believe|agree|disagree|maintain|support)|in my view|my position)\b",
        "reason": r"\b(because|one reason|this is important|the reason)\b",
        "specific_example": r"\b(for example|for instance|a clear example|consider (a|the)|when students|when people)\b",
        "explanation": r"\b(as a result|therefore|consequently|this (means|allows|helps|would)|thus)\b",
        "other_view": r"\b(i (agree|disagree) with [A-Z][a-z]+|[A-Z][a-z]+('s|\s+raises|\s+argues|\s+points? out)|while [A-Z][a-z]+)\b",
        "prompt_connection": r"\b(the question|this issue|this policy|this approach|the discussion|society|students|governments?)\b",
        "reinforcement": r"\b(for these reasons|overall|in conclusion|i maintain|should therefore)\b",
    },
}


@dataclass(frozen=True)
class StructureAnalysis:
    task_type: str
    detected_moves: list[str]
    missing_moves: list[str]
    next_action: str
    template_spam_risk: bool


def analyze_high_score_structure(text: str, task_type: str) -> StructureAnalysis:
    normalized = text.strip()
    patterns = _PATTERNS[task_type]
    detected = [name for name, pattern in patterns.items() if re.search(pattern, normalized, re.I | re.M)]
    missing = [name for name in CORE_MOVES[task_type] if name not in detected]
    repeated_frame = len(re.findall(r"\b(as .* becomes|the question of whether|i strongly agree with|while .* raises)\b", normalized, re.I)) >= 3
    if missing:
        first = missing[0]
        next_action = f"{MOVE_LABELS_KO[first]}을(를) 한 문장으로 보완하세요."
    else:
        next_action = "각 근거가 질문에 직접 연결되는지 마지막으로 검토하세요."
    return StructureAnalysis(task_type, detected, missing, next_action, repeated_frame)


def structure_guide(text: str, task_type: str) -> dict:
    result = analyze_high_score_structure(text, task_type)
    starters = (
        ["I believe this matters because...", "One practical example is...", "This would help by..."]
        if task_type == "academic_discussion"
        else ["I am writing regarding...", "Could you please...?", "Thank you for your assistance."]
    )
    return {
        "task_type": task_type,
        "detected": [MOVE_LABELS_KO[x] for x in result.detected_moves],
        "missing": [MOVE_LABELS_KO[x] for x in result.missing_moves],
        "next_action": result.next_action,
        "template_spam_risk": result.template_spam_risk,
        "safe_sentence_starters": starters,
    }
