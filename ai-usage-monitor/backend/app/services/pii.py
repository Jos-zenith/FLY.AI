import re
from dataclasses import dataclass
from typing import List

try:
    from transformers import pipeline
except ImportError:  # pragma: no cover - optional dependency in minimal environments
    pipeline = None

# --- Regex layer: structured, fixed-format PII ---
REGEX_PATTERNS = {
    "PHONE": re.compile(r"\b(?:\+?\d{1,3}[-\s]?)?(?:\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4})\b"),
    "EMAIL": re.compile(r"\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b"),
    "PAN": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    "AADHAAR": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "CREDIT_CARD": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
}

# --- NER layer: contextual entities ---
_ner_pipeline = None


def get_ner():
    global _ner_pipeline
    if pipeline is None:
        return None
    if _ner_pipeline is None:
        _ner_pipeline = pipeline(
            "ner",
            model="dslim/bert-base-NER",
            aggregation_strategy="simple",
        )
    return _ner_pipeline


NER_LABEL_MAP = {"PER": "NAME", "ORG": "ORG", "LOC": "LOCATION"}


@dataclass
class Span:
    start: int
    end: int
    label: str
    source: str  # "regex" | "ner"
    score: float = 1.0


def detect(text: str) -> List[Span]:
    spans: List[Span] = []

    # regex pass
    for label, pattern in REGEX_PATTERNS.items():
        for match in pattern.finditer(text or ""):
            spans.append(Span(match.start(), match.end(), label, "regex"))

    # NER pass
    ner = get_ner()
    if ner is not None:
        for ent in ner(text):
            label = NER_LABEL_MAP.get(ent.get("entity_group") or ent.get("entity"))
            if label:
                spans.append(
                    Span(
                        int(ent["start"]),
                        int(ent["end"]),
                        label,
                        "ner",
                        ent.get("score", 1.0),
                    )
                )

    return _resolve_overlaps(spans)


def _resolve_overlaps(spans: List[Span]) -> List[Span]:
    if not spans:
        return []

    def priority(span: Span) -> tuple[int, int, float]:
        source_rank = 1 if span.source == "regex" else 0
        return (source_rank, span.end - span.start, span.score)

    kept: List[Span] = []
    for span in sorted(spans, key=lambda s: (s.start, -priority(s)[1], -priority(s)[0], -s.score)):
        overlap_with_existing = False
        for idx, existing in enumerate(kept):
            if span.start < existing.end and span.end > existing.start:
                overlap_with_existing = True
                if priority(span) > priority(existing):
                    kept[idx] = span
                break
        if not overlap_with_existing:
            kept.append(span)

    return sorted(kept, key=lambda s: (s.start, s.end))


def detect_pii(text: str):
    return [
        {
            "type": span.label,
            "value": (text or "")[span.start:span.end],
            "source": span.source,
            "score": span.score,
        }
        for span in detect(text)
    ]


def redact(text: str) -> tuple[str, dict]:
    spans = detect(text)
    spans = sorted(spans, key=lambda s: (s.start, -(s.end - s.start), -s.score), reverse=True)
    counts: dict[str, int] = {}
    redacted_text = text
    for span in spans:
        if span.start < 0 or span.end > len(redacted_text):
            continue
        redacted_text = redacted_text[:span.start] + f"<{span.label}>" + redacted_text[span.end:]
        counts[span.label] = counts.get(span.label, 0) + 1
    return redacted_text, counts


def redact_pii(text: str):
    redacted_text, _ = redact(text)
    return redacted_text
