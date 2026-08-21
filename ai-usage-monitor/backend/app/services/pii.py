import re
from dataclasses import dataclass
from typing import List

try:
    from transformers import pipeline
except ImportError:  # pragma: no cover - optional dependency in minimal environments
    pipeline = None


REGEX_PATTERNS = {
    "PHONE": re.compile(r"\b(?:\+?\d{1,3}[-\s]?)?(?:\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4})\b"),
    "EMAIL": re.compile(r"\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b"),
    "PAN": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    "AADHAAR": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "CREDIT_CARD": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
}

# Trigger-word heuristic for NAME, e.g. "reminder email to Ramesh" or
# "Dear John Smith". This exists because the optional NER pipeline below
# depends on a model backend (torch/tensorflow) that is NOT pinned in
# requirements.txt -- on a default `pip install -r requirements.txt`,
# get_ner() fails to load and NAME detection would otherwise never fire at
# all, silently. That would break the project's own headline example
# ("Ramesh" -> "<NAME>") on a clean install with no NER extras.
#
# This is a narrow, explicitly best-effort substitute, not a real NER
# model: it only catches a capitalized name directly after one of a small
# set of trigger words, so it misses names with no trigger word ("call
# Ramesh back") and false-positives on capitalized non-names that happen
# to follow a trigger ("access to Production", "thanks to Everyone"). See
# the "PII detection limits" section in the README.
NAME_TRIGGER_PATTERN = re.compile(
    r"\b(?:to|for|dear|hi|hello|regards|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b"
)

_ner_pipeline = None
_ner_load_failed = False


def get_ner():
    """Lazily load the optional NER pipeline.

    Loading can fail for reasons other than the package being absent --
    no network access to fetch model weights, no disk space, an
    incompatible transformers/torch build, etc. The original code only
    caught RuntimeError and never remembered a failed load, so a bad
    environment meant every single request re-attempted the same slow,
    doomed model load. We now catch any load failure and cache it, so
    the app degrades once to regex-only detection instead of paying that
    cost (and risking new failure modes) on every request.
    """
    global _ner_pipeline, _ner_load_failed
    if pipeline is None or _ner_load_failed:
        return None
    if _ner_pipeline is None:
        try:
            _ner_pipeline = pipeline(
                "ner",
                model="dslim/bert-base-NER",
                aggregation_strategy="simple",
            )
        except Exception:
            _ner_load_failed = True
            return None
    return _ner_pipeline


NER_LABEL_MAP = {"PER": "NAME", "ORG": "ORG", "LOC": "LOCATION"}


@dataclass
class Span:
    start: int
    end: int
    label: str
    source: str
    score: float = 1.0


def _luhn_checksum_valid(digits: str) -> bool:
    """Standard Luhn (mod-10) check used by real card issuers.

    Without this, the CREDIT_CARD regex flags any 13-16 digit run --
    order numbers, tracking IDs, ticket numbers -- as a card number.
    Requiring a valid Luhn checksum cuts that false-positive rate
    sharply, since an arbitrary digit run only passes by chance ~1 in 10
    times, while every real card number is constructed to pass it.
    """
    total = 0
    parity = len(digits) % 2
    for index, char in enumerate(digits):
        value = int(char)
        if index % 2 == parity:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def _detect_heuristic_names(text: str) -> List[Span]:
    spans: List[Span] = []
    for match in NAME_TRIGGER_PATTERN.finditer(text or ""):
        # Redact only the captured name (group 1), not the trigger word
        # in front of it -- "to Ramesh" should become "to <NAME>", not
        # "<NAME>".
        spans.append(Span(match.start(1), match.end(1), "NAME", "heuristic", score=0.6))
    return spans


def detect(text: str) -> List[Span]:
    spans: List[Span] = []

    for label, pattern in REGEX_PATTERNS.items():
        for match in pattern.finditer(text or ""):
            if label == "CREDIT_CARD":
                candidate_digits = re.sub(r"[ -]", "", match.group())
                if not (13 <= len(candidate_digits) <= 19 and _luhn_checksum_valid(candidate_digits)):
                    # Doesn't pass the Luhn checksum -- treat it as a
                    # non-card digit run rather than redacting it as PII.
                    continue
            spans.append(Span(match.start(), match.end(), label, "regex"))

    spans.extend(_detect_heuristic_names(text))

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


def detect_pii(text: str, include_values: bool = False):
    findings = []
    for span in detect(text):
        item = {
            "type": span.label,
            "source": span.source,
            "score": span.score,
        }
        if include_values:
            item["value"] = (text or "")[span.start:span.end]
        findings.append(item)
    return findings


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
