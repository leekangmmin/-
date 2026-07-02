"""Shadow mode 비교 리포트 — 휴리스틱 점수 vs AI provider 점수.

이 모듈이 만드는 리포트는 **내부 비교용**이며 사용자에게 노출되지 않는다.
프로덕션 채점 경로(app/scorer.py)는 이 모듈의 존재와 무관하게 항상 그대로
동작한다 (app/main.py의 evaluate()는 이 모듈을 import하지 않는다).

기존 사용자 평가 결과(data/submissions.db)는 이 모듈이 절대 건드리지 않는다.
shadow 결과는 완전히 별도의 저장소(data/shadow_assessments.db)에만 기록한다.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

from app.scoring_provider import ScoringInput, ScoringProvider, ShadowScoreResult
from app.versions import (
    EXAM_SPEC_VERSION,
    GRAMMAR_RULES_VERSION,
    RESULT_SCHEMA_VERSION,
    RUBRIC_VERSION,
    SCORING_ENGINE_VERSION,
)

SHADOW_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "shadow_assessments.db"

# app/claude_provider.CLAUDE_PROMPT_VERSION 등 provider별 prompt version과 별개로,
# shadow 비교 리포트 스키마 자체의 버전.
SHADOW_SCHEMA_VERSION = "2.0.0"


@dataclass
class ShadowComparisonReport:
    # 식별 정보
    assessment_id: str
    comparison_id: str  # assessment_id의 별칭 (하위 호환용 — 항상 동일한 값)
    historical_submission_id: Optional[int]
    created_at: str

    # provider/버전 정보 — 어떤 기준·모델로 만들어진 비교인지 재현 가능하게 한다
    provider: str
    model: str
    prompt_version: str
    rubric_version: str
    grammar_rules_version: str
    exam_spec_version: str
    schema_version: str  # 이 리포트 자체의 스키마 버전 (SHADOW_SCHEMA_VERSION)
    heuristic_scoring_engine_version: str

    task_type: str

    # 점수 비교
    heuristic_score_0_5: float
    ai_raw_score_0_5: float  # critic 조정 전 draft.overall_draft_score
    ai_reconciled_score_0_5: float  # critic 조정 후 최종 점수
    score_delta: float  # ai_reconciled - heuristic

    dimension_scores: list[dict[str, Any]] = field(default_factory=list)  # AI가 매긴 차원별 점수 (참고용, heuristic과 차원 이름 체계가 다름)

    # evidence/품질 지표
    evidence_total: int = 0
    evidence_verified: int = 0
    evidence_success_rate: float = 1.0
    hallucinated_evidence_count: int = 0
    retry_count: int = 0
    invalid_assessment: bool = False
    schema_valid: bool = True

    critic_severity: str = "none"
    critic_flagged_dimensions: list[str] = field(default_factory=list)
    confidence: str = "low"

    # 성능/비용
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: Optional[float] = None

    failure_reason: Optional[str] = None
    reason_codes: list[str] = field(default_factory=list)


def _conn() -> sqlite3.Connection:
    SHADOW_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SHADOW_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


_COLUMN_DEFS: dict[str, str] = {
    "assessment_id": "TEXT PRIMARY KEY",
    "comparison_id": "TEXT",
    "historical_submission_id": "INTEGER",
    "created_at": "TEXT NOT NULL",
    "provider": "TEXT NOT NULL",
    "model": "TEXT NOT NULL",
    "prompt_version": "TEXT NOT NULL",
    "rubric_version": "TEXT NOT NULL",
    "grammar_rules_version": "TEXT NOT NULL",
    "exam_spec_version": "TEXT NOT NULL",
    "schema_version": "TEXT NOT NULL",
    "heuristic_scoring_engine_version": "TEXT NOT NULL",
    "task_type": "TEXT NOT NULL",
    "heuristic_score_0_5": "REAL NOT NULL",
    "ai_raw_score_0_5": "REAL NOT NULL",
    "ai_reconciled_score_0_5": "REAL NOT NULL",
    "score_delta": "REAL NOT NULL",
    "dimension_scores": "TEXT NOT NULL DEFAULT '[]'",
    "evidence_total": "INTEGER NOT NULL DEFAULT 0",
    "evidence_verified": "INTEGER NOT NULL DEFAULT 0",
    "evidence_success_rate": "REAL NOT NULL DEFAULT 1.0",
    "hallucinated_evidence_count": "INTEGER NOT NULL DEFAULT 0",
    "retry_count": "INTEGER NOT NULL DEFAULT 0",
    "invalid_assessment": "INTEGER NOT NULL DEFAULT 0",
    "schema_valid": "INTEGER NOT NULL DEFAULT 1",
    "critic_severity": "TEXT NOT NULL DEFAULT 'none'",
    "critic_flagged_dimensions": "TEXT NOT NULL DEFAULT '[]'",
    "confidence": "TEXT NOT NULL DEFAULT 'low'",
    "latency_ms": "REAL NOT NULL DEFAULT 0",
    "input_tokens": "INTEGER NOT NULL DEFAULT 0",
    "output_tokens": "INTEGER NOT NULL DEFAULT 0",
    "estimated_cost_usd": "REAL",
    "failure_reason": "TEXT",
    "reason_codes": "TEXT NOT NULL DEFAULT ''",
}


def init_shadow_db() -> None:
    """테이블이 없으면 생성하고, 있으면 누락된 컬럼만 추가한다(기존 로컬 데이터 보존).

    v1 스키마(comparison_id가 PRIMARY KEY)는 v2(assessment_id가 PRIMARY KEY)와
    기본 키 컬럼 자체가 다르다 — sqlite는 ALTER TABLE로 PRIMARY KEY를 바꿀 수
    없으므로, v1 테이블이 감지되면 데이터를 지우지 않고 `shadow_comparisons_v1_legacy`로
    이름을 바꿔 보존한 뒤 새 스키마로 테이블을 새로 만든다. 이 DB는 순수 내부
    비교용 개발 데이터지만, 그래도 "안전한 마이그레이션 경로 없이 기존 데이터를
    건드리지 않는다"는 원칙을 지킨다.
    """
    with _conn() as conn:
        existing_cols = {
            row["name"] for row in conn.execute("PRAGMA table_info(shadow_comparisons)")
        }
        if existing_cols and "assessment_id" not in existing_cols:
            conn.execute(
                "ALTER TABLE shadow_comparisons RENAME TO shadow_comparisons_v1_legacy"
            )
            existing_cols = set()

        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS shadow_comparisons (
                {", ".join(f"{name} {ddl}" for name, ddl in _COLUMN_DEFS.items())}
            )
            """
        )
        existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(shadow_comparisons)")}
        for name, ddl in _COLUMN_DEFS.items():
            if name not in existing_cols:
                if "PRIMARY KEY" in ddl:
                    continue
                col_ddl = ddl.replace("NOT NULL", "").strip()
                conn.execute(f"ALTER TABLE shadow_comparisons ADD COLUMN {name} {col_ddl}")


def run_shadow_comparison(
    essay_text: str,
    prompt_text: str,
    task_type: str,
    heuristic_score_0_5: float,
    provider: ScoringProvider,
    persist: bool = True,
    historical_submission_id: int | None = None,
) -> ShadowComparisonReport:
    scoring_input = ScoringInput(essay_text=essay_text, prompt_text=prompt_text, task_type=task_type)

    started = time.perf_counter()
    try:
        result: ShadowScoreResult = provider.run(scoring_input)
        failure_reason: str | None = None
    except Exception as exc:  # noqa: BLE001 — provider 실패를 리포트에 기록하고 앱은 계속 진행
        from app.scoring_provider import (
            AssessmentCritique, DimensionScoreResult, FeedbackResult,
            InputAnalysis, InputValidation,
        )

        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        result = ShadowScoreResult(
            input_validation=InputValidation(is_scorable=False, reason_codes=["provider_exception"]),
            analysis=InputAnalysis(), draft=DimensionScoreResult(),
            critique=AssessmentCritique(), final_score_0_5=0.0, confidence="low",
            feedback=FeedbackResult(), schema_valid=False, evidence_total=0, evidence_verified=0,
            invalid_assessment=True,
        )
        failure_reason = f"{type(exc).__name__}: {exc}"

    latency_ms = round((time.perf_counter() - started) * 1000, 3)

    evidence_rate = (
        result.evidence_verified / result.evidence_total if result.evidence_total else 1.0
    )

    model = getattr(provider, "cfg", None)
    model_name = getattr(model, "model", "not-applicable") if model else "not-applicable"
    prompt_version = getattr(
        __import__("app.claude_provider", fromlist=["CLAUDE_PROMPT_VERSION"]), "CLAUDE_PROMPT_VERSION", "n/a"
    ) if provider.id == "claude" else "not-applicable-mock"

    usage = getattr(provider, "last_usage", {"input_tokens": 0, "output_tokens": 0})
    estimated_cost = None
    if provider.id == "claude":
        from app.claude_provider import estimate_cost_usd
        estimated_cost = estimate_cost_usd(model_name, usage.get("input_tokens", 0), usage.get("output_tokens", 0))

    assessment_id = str(uuid.uuid4())
    report = ShadowComparisonReport(
        assessment_id=assessment_id,
        comparison_id=assessment_id,
        historical_submission_id=historical_submission_id,
        created_at=datetime.now(UTC).isoformat(),
        provider=provider.id,
        model=model_name,
        prompt_version=prompt_version,
        rubric_version=RUBRIC_VERSION,
        grammar_rules_version=GRAMMAR_RULES_VERSION,
        exam_spec_version=EXAM_SPEC_VERSION,
        schema_version=SHADOW_SCHEMA_VERSION,
        heuristic_scoring_engine_version=SCORING_ENGINE_VERSION,
        task_type=task_type,
        heuristic_score_0_5=heuristic_score_0_5,
        ai_raw_score_0_5=result.draft.overall_draft_score,
        ai_reconciled_score_0_5=result.final_score_0_5,
        score_delta=round(result.final_score_0_5 - heuristic_score_0_5, 3),
        dimension_scores=[
            {"dimension_id": d.dimension_id, "score": d.score, "max_score": d.max_score}
            for d in result.draft.dimensions
        ],
        evidence_total=result.evidence_total,
        evidence_verified=result.evidence_verified,
        evidence_success_rate=round(evidence_rate, 3),
        hallucinated_evidence_count=result.evidence_total - result.evidence_verified,
        retry_count=result.retry_count,
        invalid_assessment=result.invalid_assessment,
        schema_valid=result.schema_valid,
        critic_severity=result.critique.severity,
        critic_flagged_dimensions=result.critique.flagged_dimension_ids,
        confidence=result.confidence,
        latency_ms=latency_ms,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        estimated_cost_usd=estimated_cost,
        failure_reason=failure_reason,
        reason_codes=result.reason_codes,
    )

    if persist:
        init_shadow_db()
        with _conn() as conn:
            row = asdict(report)
            row["dimension_scores"] = json.dumps(report.dimension_scores, ensure_ascii=False)
            row["critic_flagged_dimensions"] = json.dumps(report.critic_flagged_dimensions, ensure_ascii=False)
            row["reason_codes"] = ",".join(report.reason_codes)
            row["invalid_assessment"] = int(report.invalid_assessment)
            row["schema_valid"] = int(report.schema_valid)

            columns = list(_COLUMN_DEFS.keys())
            placeholders = ", ".join("?" for _ in columns)
            conn.execute(
                f"INSERT INTO shadow_comparisons ({', '.join(columns)}) VALUES ({placeholders})",
                tuple(row[c] for c in columns),
            )

    return report


def summarize_comparisons(limit: int = 500) -> dict[str, Any]:
    init_shadow_db()
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM shadow_comparisons ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    rows = [dict(r) for r in rows]
    if not rows:
        return {
            "count": 0, "avg_score_delta": None, "avg_evidence_success_rate": None,
            "avg_latency_ms": None, "schema_success_rate": None, "retry_rate": None,
            "invalid_assessment_rate": None, "hallucinated_evidence_count_total": None,
            "total_estimated_cost_usd": None,
        }

    def avg(key: str) -> float:
        return round(sum(r[key] for r in rows) / len(rows), 4)

    costs = [r["estimated_cost_usd"] for r in rows if r.get("estimated_cost_usd") is not None]

    return {
        "count": len(rows),
        "avg_score_delta": avg("score_delta"),
        "avg_evidence_success_rate": avg("evidence_success_rate"),
        "avg_latency_ms": avg("latency_ms"),
        "schema_success_rate": round(sum(r["schema_valid"] for r in rows) / len(rows), 4),
        "retry_rate": round(sum(1 for r in rows if r["retry_count"] > 0) / len(rows), 4),
        "invalid_assessment_rate": round(sum(r["invalid_assessment"] for r in rows) / len(rows), 4),
        "hallucinated_evidence_count_total": sum(r["hallucinated_evidence_count"] for r in rows),
        "total_estimated_cost_usd": round(sum(costs), 6) if costs else None,
    }
