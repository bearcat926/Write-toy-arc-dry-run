"""Milestone 1: Hash encoding failure tests."""
import pytest
from pathlib import Path
from novel_workflow.schemas.hash_utils import canonical_sha256_file


def test_utf8_valid_passes(tmp_path: Path):
    f = tmp_path / "valid.md"
    f.write_bytes("hello\n".encode("utf-8"))
    result = canonical_sha256_file(f)
    assert isinstance(result, str) and len(result) == 64


def test_utf8_bom_passes(tmp_path: Path):
    f = tmp_path / "bom.md"
    f.write_bytes(b"\xef\xbb\xbfhello\n")
    result = canonical_sha256_file(f)
    assert isinstance(result, str)


def test_invalid_utf8_fails(tmp_path: Path):
    f = tmp_path / "invalid.md"
    # Write invalid UTF-8 bytes (0xFF is never valid in UTF-8)
    f.write_bytes(b"\xff\xfe hello\n")
    with pytest.raises(UnicodeDecodeError):
        canonical_sha256_file(f)


def test_latin1_fails(tmp_path: Path):
    f = tmp_path / "latin1.md"
    f.write_bytes("café\n".encode("latin-1"))
    with pytest.raises(UnicodeDecodeError):
        canonical_sha256_file(f)


def test_json_invalid_utf8_fails(tmp_path: Path):
    f = tmp_path / "bad.json"
    f.write_bytes(b'\xff\xfe {"a": 1}')
    with pytest.raises(UnicodeDecodeError):
        canonical_sha256_file(f)
