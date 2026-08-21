import app.services.pii as pii_module
from app.services.pii import detect, redact, redact_pii


def test_detect_pii_email_and_phone():
    text = "Contact me at alice@example.com or 5551234567"
    findings = detect(text)
    labels = {item.label for item in findings}
    assert "EMAIL" in labels
    assert "PHONE" in labels


def test_redact_pii_replaces_values_and_returns_counts():
    text = "My email is alice@example.com and phone is 5551234567"
    redacted, counts = redact(text)
    assert "alice@example.com" not in redacted
    assert "5551234567" not in redacted
    assert "<EMAIL>" in redacted or "<PHONE>" in redacted
    assert counts.get("EMAIL", 0) >= 1
    assert counts.get("PHONE", 0) >= 1
    assert redact_pii(text) == redacted


def test_valid_luhn_card_number_is_flagged_as_credit_card():
    # 4111111111111111 is the standard Visa test number and passes Luhn.
    text = "Card on file: 4111111111111111"
    findings = detect(text)
    labels = {item.label for item in findings}
    assert "CREDIT_CARD" in labels


def test_order_number_that_fails_luhn_is_not_flagged_as_credit_card():
    # A 16-digit order/tracking number that does not pass the Luhn
    # checksum should not be redacted as a credit card -- this is the
    # false-positive case a bare digit-length regex used to catch.
    text = "Order reference: 1234567890123456"
    findings = detect(text)
    labels = {item.label for item in findings}
    assert "CREDIT_CARD" not in labels


def test_ner_load_failure_is_cached_and_not_retried(monkeypatch):
    monkeypatch.setattr(pii_module, "_ner_pipeline", None)
    monkeypatch.setattr(pii_module, "_ner_load_failed", False)

    call_count = {"n": 0}

    def _boom(*args, **kwargs):
        call_count["n"] += 1
        raise OSError("no network access to fetch model weights")

    monkeypatch.setattr(pii_module, "pipeline", _boom)

    assert pii_module.get_ner() is None
    assert pii_module.get_ner() is None
    assert call_count["n"] == 1
