from georevive.ingest.report import generate, terminal_summary
from georevive.registry import upsert_source


def test_data_report_generation(db, temp_root):
    upsert_source(
        db,
        "syn_ok",
        name="SYNTHETIC OK source",
        publisher="Test",
        url="https://example.org/a",
        licence="CC BY 4.0",
        status="downloaded",
        record_count=12,
    )
    upsert_source(
        db,
        "syn_manual",
        name="SYNTHETIC manual source",
        publisher="Test",
        url="https://example.org/b",
        licence="licence to confirm",
        status="needs_manual_request",
        error="not public",
        how_to_obtain="Email someone@example.org",
    )
    upsert_source(
        db,
        "syn_fail",
        name="SYNTHETIC failed source",
        publisher="Test",
        url="https://example.org/c",
        status="failed",
        error="HTTP 503",
    )
    md, js = generate(db)
    text = md.read_text(encoding="utf-8")
    assert "SYNTHETIC OK source" in text and "12 records" in text
    assert "## What failed and why" in text and "HTTP 503" in text
    assert "Email someone@example.org" in text
    assert "licence to confirm" in text
    assert js.exists()
    summary = terminal_summary(db)
    assert "syn_manual" in summary and "Needs manual request" in summary
