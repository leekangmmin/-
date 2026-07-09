"""반복 실행 가능한 평가 하네스.

사용법:
    .venv/bin/python -m tests.eval_harness

측정 항목:
- 오탐률: 올바른 영어 문장 세트에서 문법 오류로 계산된 건수
- 순위 보존: 품질 등급이 다른 답안 쌍의 순위 역전 여부
- 반복 채점 편차: 동일 답안 반복 평가 시 점수 차이 (결정론 검증)
- 경계 입력: 빈/짧은/이모지/인젝션 입력의 안전 처리
- 평가 시간

주의: 픽스처는 전부 합성 데이터(Tier D)다. 이 하네스는 회귀 방지용이며,
전문가 채점 데이터 대비 정확도(MAE 등)는 현재 측정 불가다.
"""

from __future__ import annotations

import time

from app.grammar import analyze_grammar
from app.scorer import SCORING_ENGINE_VERSION, score_essay
from tests.fixtures import (
    DISCUSSION_HIGH,
    DISCUSSION_INJECTION,
    DISCUSSION_LOW,
    DISCUSSION_MID,
    DISCUSSION_OFF_TOPIC,
    EMAIL_HIGH,
    EMAIL_LOW,
    EMAIL_MISSING_REQUIRED_POINT,
    TEMPLATE_SPAM,
)

# 올바른 영어 문장 세트 — 오탐이 나오면 안 된다
CORRECT_SENTENCES = [
    "She gave an example and ate an apple.",
    "It took an hour to write an honest review.",
    "I was tired yesterday, so I went home early.",
    "If it were possible, I would join the program.",
    "Compared with last year, the results improved.",
    "Students that have completed the course perform well.",
    "When I was young, I joined a debate club.",
    "Because they practiced daily, they improved quickly.",
    "I studied hard, and I passed the exam.",
    "The U.S. economy grew, e.g. in the tech sector.",
    "Does he have enough time to finish the work?",
    "Although the task was difficult, we finished it together.",
    "There are many reasons to support this policy.",
    "He suggested that I ask the professor for advice.",
    "This is an important opportunity for a university student.",
]

RANK_PAIRS = [
    ("discussion high > mid", DISCUSSION_HIGH, DISCUSSION_MID, "academic_discussion"),
    ("discussion mid > low", DISCUSSION_MID, DISCUSSION_LOW, "academic_discussion"),
    ("discussion high > low", DISCUSSION_HIGH, DISCUSSION_LOW, "academic_discussion"),
    ("discussion high > injection", DISCUSSION_HIGH, DISCUSSION_INJECTION, "academic_discussion"),
    ("email high > low", EMAIL_HIGH, EMAIL_LOW, "email"),
]


def run() -> dict:
    report: dict = {"engine": SCORING_ENGINE_VERSION}

    # 1) 오탐률
    fp = sum(analyze_grammar(s).total for s in CORRECT_SENTENCES)
    report["false_positive_count"] = fp
    report["false_positive_sentences"] = len(CORRECT_SENTENCES)

    # 2) 순위 보존
    inversions = []
    for label, better, worse, ptype in RANK_PAIRS:
        _, b = score_essay(better, ptype)
        _, w = score_essay(worse, ptype)
        if b <= w:
            inversions.append(f"{label} (better={b}, worse={w})")
    report["rank_pairs"] = len(RANK_PAIRS)
    report["rank_inversions"] = inversions

    # 3) 반복 채점 편차 (결정론이므로 0이어야 한다)
    scores = [score_essay(DISCUSSION_MID, "academic_discussion")[1] for _ in range(10)]
    report["repeat_max_deviation"] = max(scores) - min(scores)

    # 4) 경계 입력 안전성
    boundary_ok = True
    boundary_errors = []
    for label, text in [
        ("empty", ""),
        ("one word", "hello"),
        ("emoji", "I like studying 📚 with friends every single day."),
        ("injection", DISCUSSION_INJECTION),
        ("very long", DISCUSSION_HIGH * 20),
        ("html", "<script>alert(1)</script> I think school is good for students."),
    ]:
        try:
            _, s = score_essay(text, "academic_discussion")
            assert 0.0 <= s <= 5.0
        except Exception as exc:  # noqa: BLE001
            boundary_ok = False
            boundary_errors.append(f"{label}: {exc}")
    report["boundary_inputs_ok"] = boundary_ok
    report["boundary_errors"] = boundary_errors

    # 5) 인젝션 저항: 인젝션 답안이 상위 밴드를 받으면 실패
    _, inj = score_essay(DISCUSSION_INJECTION, "academic_discussion")
    report["injection_score_0_5"] = inj
    report["injection_blocked"] = inj <= 2.0

    # 6) 주제 이탈: prompt-fit 결합 시 감점되는지 (evaluate_prompt_fit 경유)
    from app.advanced import evaluate_prompt_fit
    from tests.fixtures import PROMPT_DISCUSSION_INTERNSHIP

    fit_on = evaluate_prompt_fit(PROMPT_DISCUSSION_INTERNSHIP, DISCUSSION_HIGH)["score"]
    fit_off = evaluate_prompt_fit(PROMPT_DISCUSSION_INTERNSHIP, DISCUSSION_OFF_TOPIC)["score"]
    report["prompt_fit_on_topic"] = fit_on
    report["prompt_fit_off_topic"] = fit_off
    report["off_topic_detected"] = fit_off < fit_on

    from tests.fixtures import PROMPT_EMAIL_EXTENSION

    email_fit_full = evaluate_prompt_fit(PROMPT_EMAIL_EXTENSION, EMAIL_HIGH)
    email_fit_missing = evaluate_prompt_fit(PROMPT_EMAIL_EXTENSION, EMAIL_MISSING_REQUIRED_POINT)
    spam_fit = evaluate_prompt_fit(PROMPT_DISCUSSION_INTERNSHIP, TEMPLATE_SPAM)
    report["email_requirement_full"] = email_fit_full["score"]
    report["email_requirement_missing"] = email_fit_missing["score"]
    report["email_missing_required_detected"] = (
        email_fit_missing["score"] < email_fit_full["score"]
        and any("required:" in item for item in email_fit_missing["missing_keywords"])
    )
    report["template_spam_score"] = spam_fit["score"]
    report["template_spam_detected"] = spam_fit["score"] <= 2.5 and "Template risk" in spam_fit["reason_en"]

    # 7) 평가 시간
    started = time.perf_counter()
    for _ in range(20):
        score_essay(DISCUSSION_HIGH, "academic_discussion")
    report["avg_scoring_ms"] = round((time.perf_counter() - started) / 20 * 1000, 2)

    return report


def main() -> None:
    report = run()
    from tests.fixtures import EVALUATION_DATASET_VERSION

    print(f"=== Evaluation Harness (engine {report['engine']}, dataset v{EVALUATION_DATASET_VERSION}) ===")
    print(f"오탐(올바른 문장 {report['false_positive_sentences']}개): {report['false_positive_count']}건")
    print(f"순위 역전: {len(report['rank_inversions'])}/{report['rank_pairs']} {report['rank_inversions'] or ''}")
    print(f"반복 채점 최대 편차: {report['repeat_max_deviation']}")
    print(f"경계 입력 안전: {'OK' if report['boundary_inputs_ok'] else report['boundary_errors']}")
    print(f"인젝션 답안 점수(0-5): {report['injection_score_0_5']} (상위밴드 차단: {report['injection_blocked']})")
    print(f"주제 적합성 on/off-topic: {report['prompt_fit_on_topic']} / {report['prompt_fit_off_topic']} (이탈 감지: {report['off_topic_detected']})")
    print(f"이메일 요구사항 full/missing: {report['email_requirement_full']} / {report['email_requirement_missing']} (누락 감지: {report['email_missing_required_detected']})")
    print(f"템플릿 스팸 prompt-fit: {report['template_spam_score']} (감지: {report['template_spam_detected']})")
    print(f"평균 채점 시간: {report['avg_scoring_ms']}ms")

    failures = []
    if report["false_positive_count"] > 0:
        failures.append("오탐 존재")
    if report["rank_inversions"]:
        failures.append("순위 역전")
    if report["repeat_max_deviation"] > 0:
        failures.append("반복 채점 불안정")
    if not report["boundary_inputs_ok"]:
        failures.append("경계 입력 실패")
    if not report["injection_blocked"]:
        failures.append("인젝션 미차단")
    if not report["off_topic_detected"]:
        failures.append("주제 이탈 미감지")
    if not report["email_missing_required_detected"]:
        failures.append("이메일 요구사항 누락 미감지")
    if not report["template_spam_detected"]:
        failures.append("템플릿 스팸 미감지")

    if failures:
        print(f"\nFAIL: {', '.join(failures)}")
        raise SystemExit(1)
    print("\nPASS: 모든 품질 게이트 통과")


if __name__ == "__main__":
    main()
