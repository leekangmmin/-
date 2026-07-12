"""Local-only corpus ingestion. Public outputs are aggregate and quote-free."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path
from statistics import mean

from app.advanced import detect_prompt_type
from app.corpus_schema import HighScoreSample
from app.high_score_patterns import analyze_high_score_structure
from app.scorer import analyze_essay

SUPPORTED_SUFFIXES = {".txt", ".md", ".csv", ".pdf"}


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("\x00", "")
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL]", text)
    text = re.sub(r"\b(?:\+?\d[\d -]{7,}\d)\b", "[PHONE]", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def _read_pdf(path: Path) -> str:
    try:
        proc = subprocess.run(["pdftotext", "-layout", str(path), "-"], check=True, capture_output=True, text=True)
        return proc.stdout
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise ValueError("PDF ingestion requires the local pdftotext utility") from exc


def _text_chunks(text: str) -> list[str]:
    chunks = re.split(r"(?:\n\s*={3,}\s*\n|\n\s*---+\s*\n|\f)", text)
    return [c.strip() for c in chunks if len(re.findall(r"[A-Za-z']+", c)) >= 40]


def _pdf_chunks(text: str) -> list[str]:
    """Split common answer-book layouts without retaining titles as separate records."""
    text = text.replace("\f", "\n")
    email_start = re.search(r"(?m)^\s*1\.\s+", text)
    discussion_part = text[:email_start.start()] if email_start else text
    email_part = text[email_start.start():] if email_start else ""

    discussions: list[str] = []
    start = 0
    for match in re.finditer(r"(?ms)^For these reasons,.*?(?:\n\s*\n|\Z)", discussion_part):
        chunk = discussion_part[start:match.end()].strip()
        if len(re.findall(r"[A-Za-z']+", chunk)) >= 40:
            discussions.append(chunk)
        start = match.end()

    emails = re.split(r"(?m)(?=^\s*\d+\.\s+)", email_part)
    email_chunks = [c.strip() for c in emails if len(re.findall(r"[A-Za-z']+", c)) >= 40]
    return discussions + email_chunks or _text_chunks(text)


def _row_texts(path: Path) -> list[tuple[str, dict[str, str]]]:
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        return [(r.get("answer_text") or r.get("essay_text") or r.get("answer") or "", r) for r in rows]
    is_pdf = path.suffix.lower() == ".pdf"
    raw = _read_pdf(path) if is_pdf else path.read_text(encoding="utf-8-sig")
    return [(chunk, {}) for chunk in (_pdf_chunks(raw) if is_pdf else _text_chunks(raw))]


def ingest_path(path: str | Path) -> list[HighScoreSample]:
    root = Path(path)
    files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.suffix.lower() in SUPPORTED_SUFFIXES)
    samples: list[HighScoreSample] = []
    seen: set[str] = set()
    for source in files:
        for index, (raw, meta) in enumerate(_row_texts(source), 1):
            answer = _normalize(raw)
            if len(re.findall(r"[A-Za-z']+", answer)) < 40:
                continue
            digest = hashlib.sha256(answer.encode()).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)
            task_type = meta.get("task_type") or detect_prompt_type(answer)
            moves = analyze_high_score_structure(answer, task_type)
            samples.append(HighScoreSample(
                sample_id=f"{source.stem}-{index}-{digest[:10]}", task_type=task_type,
                prompt_id=meta.get("prompt_id") or None, prompt_text=meta.get("prompt_text") or None,
                answer_text=answer, score=float(meta["score"]) if meta.get("score") else None,
                score_label=meta.get("score_label") or None, source_type=meta.get("source_type", "unknown"),
                permission_status=meta.get("permission_status", "unknown"), can_redistribute=False,
                structure_tags=moves.detected_moves, quality_tags=[], content_hash=digest,
            ))
    return samples


def safe_aggregate(samples: list[HighScoreSample]) -> dict:
    by_type: dict[str, list[HighScoreSample]] = {}
    for sample in samples:
        by_type.setdefault(sample.task_type, []).append(sample)
    result = {"schema_version": "1.0", "sample_count": len(samples), "task_types": {}}
    for task_type, group in sorted(by_type.items()):
        metrics = [analyze_essay(s.answer_text) for s in group]
        moves = {m: sum(m in s.structure_tags for s in group) for m in sorted({x for s in group for x in s.structure_tags})}
        result["task_types"][task_type] = {
            "count": len(group), "average_word_count": round(mean(m.word_count for m in metrics), 1),
            "average_sentence_count": round(mean(m.sentence_count for m in metrics), 1),
            "average_paragraph_count": round(mean(m.paragraph_count for m in metrics), 1),
            "move_detection_rates": {k: round(v / len(group), 3) for k, v in moves.items()},
        }
    return result


def write_safe_summary(samples: list[HighScoreSample], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(safe_aggregate(samples), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
