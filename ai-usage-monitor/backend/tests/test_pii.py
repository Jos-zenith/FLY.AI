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
