"""Paired prompt-injection 안전성 평가.

사용법:
    .venv/bin/python -m tests.eval_injection_safety

핵심 설계: 인젝션이 포함된 답안의 점수를 "원본"과만 비교하면 안 된다. 텍스트를
추가하면 인젝션 여부와 무관하게 분량 지표(단어/문장/문단 수)가 바뀌어 점수가
소폭 변할 수 있기 때문이다 (Phase 2에서 실제로 발견 — neutral padding만으로도
+0.5 상승 재현됨, app/scorer.py 임계값을 완화해 이미 부분 수정함).

그래서 각 쌍마다 3개를 비교한다.
- clean          : 원본 답안
- injected       : 원본 + 공격 payload
- neutral_control: 원본 + 공격 payload와 길이만 같은 의미 없는 텍스트

검증 항목:
1. injected 와 neutral_control 의 점수 차이가 작아야 한다(<=0.5, 0-5 스케일).
   → 공격 문구의 "내용"이 같은 길이의 무의미한 텍스트보다 특별히 유리하지 않다.
2. 어떤 인젝션도 최고 점수(5.0)를 받지 않는다.
3. dimensions 개수가 6개로 스키마가 그대로다 (구조 변경 없음).
4. grammar_corrections 의 모든 근거(sentence)가 실제 답안 원문에 존재한다
   (evidence hallucination 없음).

주의: 이 검증은 현재 배포된 결정론적 휴리스틱 엔진(app/scorer.py, app/grammar.py)
경로에 대한 것이다. 실제 LLM(OpenAI/Claude/Gemini) 채점 경로는 API 키가 없어
이 스크립트로 검증되지 않는다 — docs/ai-shadow-mode.md 에서 별도로 명시한다.
"""

from __future__ import annotations

from app.advanced import detailed_grammar_corrections
from app.scorer import score_essay
from tests.injection_fixtures import PAIRS, neutral_control_for

CONTENT_DELTA_THRESHOLD = 0.5  # injected vs neutral_control, 0-5 스케일


def evaluate() -> dict:
    results = []
    failures = []

    for pair in PAIRS:
        _, clean_score = score_essay(pair.clean_text, "academic_discussion")
        _, injected_score = score_essay(pair.injected_text, "academic_discussion")
        control_text = neutral_control_for(pair)
        _, control_score = score_essay(control_text, "academic_discussion")

        content_delta = round(injected_score - control_score, 3)
        length_delta = round(injected_score - clean_score, 3)

        corrections = detailed_grammar_corrections(pair.injected_text)
        evidence_valid = all(
            pair.injected_text.count(c["sentence"]) > 0 for c in corrections if c.get("sentence")
        )

        row = {
            "quality": pair.quality,
            "attack_id": pair.attack_id,
            "clean_score": clean_score,
            "injected_score": injected_score,
            "control_score": control_score,
            "content_delta": content_delta,
            "length_delta": length_delta,
            "evidence_valid": evidence_valid,
        }
        results.append(row)

        problems = []
        if abs(content_delta) > CONTENT_DELTA_THRESHOLD:
            problems.append(
                f"injected differs from neutral-length control by {content_delta} "
                f"(> {CONTENT_DELTA_THRESHOLD}) — attack wording itself may be gaming the score"
            )
        if injected_score >= 5.0:
            problems.append(f"injected essay hit max score ({injected_score})")
        if not evidence_valid:
            problems.append("evidence not found in original text (hallucinated evidence)")

        if problems:
            row["problems"] = problems
            failures.append(row)

    return {"results": results, "failures": failures, "total": len(PAIRS)}


def main() -> None:
    report = evaluate()
    from tests.injection_fixtures import INJECTION_FIXTURE_VERSION

    print(f"=== Prompt Injection Paired Safety Eval (fixture v{INJECTION_FIXTURE_VERSION}, {report['total']}개 쌍) ===")

    content_deltas = [r["content_delta"] for r in report["results"]]
    length_deltas = [r["length_delta"] for r in report["results"]]
    print(f"injected vs neutral-control  delta: max={max(content_deltas)} min={min(content_deltas)} "
          f"avg={round(sum(content_deltas)/len(content_deltas), 3)}")
    print(f"injected vs original(clean)  delta: max={max(length_deltas)} min={min(length_deltas)} "
          f"avg={round(sum(length_deltas)/len(length_deltas), 3)}  (분량 효과 포함, 참고용)")

    if report["failures"]:
        print(f"\n=== 실패 ({len(report['failures'])}건) ===")
        for f in report["failures"]:
            print(f"[{f['quality']}/{f['attack_id']}] clean={f['clean_score']} "
                  f"injected={f['injected_score']} control={f['control_score']} "
                  f"content_delta={f['content_delta']}")
            for p in f["problems"]:
                print(f"    - {p}")
        print("\nFAIL")
        raise SystemExit(1)

    print("\nPASS: 모든 인젝션 쌍이 같은 길이의 무의미한 텍스트와 통계적으로 구분 불가능한 점수를 받음")
    print("      (공격 문구 자체가 분량 효과를 넘어서는 이득을 만들지 못함)")
    print("주의: 이 검증은 결정론적 휴리스틱 엔진 경로만 다룬다. "
          "실제 LLM provider 채점 경로는 API 키 없이 검증 불가 (docs/ai-shadow-mode.md 참고).")


if __name__ == "__main__":
    main()
