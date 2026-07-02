"""Build a Sentence 결정론적 채점 엔진.

채점 순서 (마스터 스펙 9장):
  1. 정규화 (대소문자/구두점/축약형 정책 적용)
  2. 정확 일치
  3. 허용 답안(alternative) 일치
  4. 구조 규칙 검사 (필수 구성요소 포함 여부·개수)
  5. 의미 동등성 보조 검사 — 현재 미구현 (아래 설명)
  6. 필요한 경우에만 AI 검토 — 현재 훅만 존재, 기본 비활성

의미 동등성(5단계)은 임베딩/의역 판단이 필요해 순수 결정론적 엔진 범위를
벗어난다. 이 엔진은 하드코딩된 허용 답안 목록(단계 3)까지만 결정론적으로
처리하고, 그 이상은 낙제 처리 후 사용자에게 "정답 후보와 다름"으로만 보고한다
(임의로 관대하게 정답 처리하지 않는다 — 공식 정답 없는 문항에 대한 허구의
관용을 만들지 않기 위함).
"""

from __future__ import annotations

import re

from app.build_a_sentence_models import BuildASentenceItem, BuildASentenceResult

ENGINE_VERSION = "build-a-sentence-1.0.0"

_CONTRACTIONS = {
    "isn't": "is not", "aren't": "are not", "wasn't": "was not", "weren't": "were not",
    "don't": "do not", "doesn't": "does not", "didn't": "did not",
    "can't": "cannot", "couldn't": "could not", "won't": "will not", "wouldn't": "would not",
    "shouldn't": "should not", "haven't": "have not", "hasn't": "has not", "hadn't": "had not",
    "i'm": "i am", "you're": "you are", "he's": "he is", "she's": "she is", "it's": "it is",
    "we're": "we are", "they're": "they are", "i've": "i have", "you've": "you have",
    "we've": "we have", "they've": "they have", "i'll": "i will", "you'll": "you will",
    "he'll": "he will", "she'll": "she will", "we'll": "we will", "they'll": "they will",
    "i'd": "i would", "you'd": "you would",
}
_EXPANDED_TO_CONTRACTED = {v: k for k, v in _CONTRACTIONS.items()}


def _apply_contraction_policy(text: str, policy: str) -> str:
    """대소문자를 보존한 채로 축약형만 치환한다 (대소문자 구분 문항에서
    case_sensitive 설정이 이 단계에서 무시되지 않도록 case-insensitive 매칭만
    사용하고 원문 케이스는 건드리지 않는다 — 단, 치환된 부분 자체는 소문자가
    된다는 한계가 있다. 축약형은 보통 고유명사가 아니므로 실무상 허용 가능한
    트레이드오프다)."""
    if policy == "require_expanded":
        for contracted, expanded in _CONTRACTIONS.items():
            text = re.sub(rf"\b{re.escape(contracted)}\b", expanded, text, flags=re.IGNORECASE)
    elif policy == "require_contracted":
        for expanded, contracted in _EXPANDED_TO_CONTRACTED.items():
            text = re.sub(rf"\b{re.escape(expanded)}\b", contracted, text, flags=re.IGNORECASE)
    # either_allowed: 변형하지 않음 (두 형태 모두 정규화 후 비교 시 별도 처리 필요)
    return text


def normalize(text: str, item: BuildASentenceItem) -> str:
    """item의 정책에 따라 제출문을 정규화한다.

    순서가 중요하다: 축약형 치환을 먼저 하고, case_sensitive 여부에 따른
    소문자 변환은 마지막에 한 번만 적용한다 (이전 버전은 축약형 치환 내부에서
    항상 lower()를 호출해 case_sensitive=True 문항에서도 대소문자 구분이
    무시되는 버그가 있었다).
    """
    result = text.strip()
    result = _apply_contraction_policy(result, item.contraction_policy)

    if item.punctuation_policy == "ignore_all":
        result = re.sub(r"[^\w\s]", "", result)
    elif item.punctuation_policy == "ignore_terminal":
        result = re.sub(r"[.!?]+$", "", result.strip())
    # strict: 구두점 그대로 유지

    if not item.case_sensitive:
        result = result.lower()

    result = re.sub(r"\s+", " ", result).strip()
    return result


def _tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z']+", text.lower())


def _structural_check(item: BuildASentenceItem, normalized_submission: str) -> tuple[bool, list[str], list[str]]:
    """필수 구성요소(source_fragments)가 모두 포함됐는지 확인한다.

    어순까지는 강제하지 않는다(정답 배열이 여러 개일 수 있으므로) — 포함 여부만
    검사해 "구조적으로 근접" 여부를 보고하는 보조 신호다. 이것만으로 정답
    처리하지 않는다 (match_type="structural_partial"은 is_correct=False로 남는다).
    """
    submission_tokens = set(_tokens(normalized_submission))
    missing: list[str] = []
    for fragment in item.source_fragments:
        fragment_tokens = _tokens(fragment)
        if fragment_tokens and not all(t in submission_tokens for t in fragment_tokens):
            missing.append(fragment)

    expected_tokens: set[str] = set()
    for fragment in item.source_fragments:
        expected_tokens.update(_tokens(fragment))
    extra = sorted(submission_tokens - expected_tokens)

    return (len(missing) == 0, missing, extra)


def score_submission(item: BuildASentenceItem, submission_text: str) -> BuildASentenceResult:
    normalized_submission = normalize(submission_text, item)

    # ── 2. 정확 일치 ──────────────────────────────────────────────────
    normalized_primary = normalize(item.primary_answer, item)
    if normalized_submission == normalized_primary:
        return BuildASentenceResult(
            item_id=item.item_id, match_type="exact", is_correct=True,
            matched_answer=item.primary_answer, normalized_submission=normalized_submission,
            feedback="정답과 정확히 일치합니다.", engine_version=ENGINE_VERSION,
        )

    # ── 3. 허용 답안 일치 ─────────────────────────────────────────────
    for alt in item.allowed_answers:
        if normalized_submission == normalize(alt.text, item):
            return BuildASentenceResult(
                item_id=item.item_id, match_type="allowed_variant", is_correct=True,
                matched_answer=alt.text, normalized_submission=normalized_submission,
                feedback=f"허용된 변형 답안과 일치합니다. ({alt.rationale})" if alt.rationale else "허용된 변형 답안과 일치합니다.",
                engine_version=ENGINE_VERSION,
            )

    # ── 4. 구조 규칙 검사 (보조 신호, 정답 처리는 하지 않음) ──────────
    structurally_complete, missing, extra = _structural_check(item, normalized_submission)
    if structurally_complete and not extra:
        return BuildASentenceResult(
            item_id=item.item_id, match_type="structural_partial", is_correct=False,
            matched_answer=None, normalized_submission=normalized_submission,
            missing_fragments=missing, extra_tokens=extra,
            feedback="필요한 구성요소는 모두 포함됐지만 정확한 정답 형태와 다릅니다. "
                     "어순이나 표현을 다시 확인하세요.",
            engine_version=ENGINE_VERSION,
        )

    # ── 5. 의미 동등성 보조 검사 — 현재 미구현 ──────────────────────
    # ── 6. AI 검토 — 현재 비활성 (훅 없음, 필요 시 ScoringProvider 연결) ─
    return BuildASentenceResult(
        item_id=item.item_id, match_type="none", is_correct=False,
        matched_answer=None, normalized_submission=normalized_submission,
        missing_fragments=missing, extra_tokens=extra,
        feedback="제공된 구성요소로 만들 수 있는 정답과 일치하지 않습니다.",
        engine_version=ENGINE_VERSION,
    )
