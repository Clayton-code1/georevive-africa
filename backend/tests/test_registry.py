import pytest

from georevive.registry import set_files, sha256_file, source_to_dict, upsert_source


def test_upsert_source_and_files(db, temp_root):
    f = temp_root / "data" / "raw" / "x.txt"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("SYNTHETIC test file", encoding="utf-8")
    src = upsert_source(
        db,
        "test_src",
        name="Test",
        publisher="Pub",
        url="https://example.org",
        licence="CC BY 4.0",
        status="downloaded",
        record_count=3,
    )
    set_files(db, src, [(f, "https://example.org/x.txt")])
    d = source_to_dict(src)
    assert d["status"] == "downloaded"
    assert d["accessed_at"] is not None
    assert d["files"][0]["sha256"] == sha256_file(f)
    assert d["files"][0]["path"] == "data/raw/x.txt"
    # idempotent: re-run replaces, does not duplicate
    set_files(db, src, [(f, "https://example.org/x.txt")])
    assert len(source_to_dict(src)["files"]) == 1


def test_invalid_status_rejected(db):
    with pytest.raises(ValueError):
        upsert_source(db, "bad", name="Bad", publisher="", url="", status="ok")


def test_sha256_known_value(tmp_path):
    p = tmp_path / "a.bin"
    p.write_bytes(b"abc")
    assert sha256_file(p) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
