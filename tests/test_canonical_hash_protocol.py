"""Milestone 1: Canonical hash protocol tests."""
import json
import pytest
from pathlib import Path
from novel_workflow.schemas.hash_utils import (
    canonicalize_text_string,
    canonicalize_text_bytes,
    canonicalize_json_for_hash,
    canonical_sha256_file,
    reject_float_values,
    get_hash_strategy_for_source,
)
from novel_workflow.schemas.enums import HashStrategy


class TestTextCanonicalization:
    def test_lf_and_crlf_same_hash(self, tmp_path: Path):
        lf_file = tmp_path / "lf.md"
        crlf_file = tmp_path / "crlf.md"
        lf_file.write_bytes(b"hello\nworld\n")
        crlf_file.write_bytes(b"hello\r\nworld\r\n")
        assert canonical_sha256_file(lf_file) == canonical_sha256_file(crlf_file)

    def test_bom_removed(self, tmp_path: Path):
        no_bom = tmp_path / "nobom.md"
        with_bom = tmp_path / "bom.md"
        no_bom.write_bytes(b"hello\n")
        with_bom.write_bytes(b"\xef\xbb\xbfhello\n")
        assert canonical_sha256_file(no_bom) == canonical_sha256_file(with_bom)

    def test_trailing_whitespace_stripped(self, tmp_path: Path):
        f1 = tmp_path / "clean.md"
        f2 = tmp_path / "trailing.md"
        f1.write_bytes(b"hello\nworld\n")
        f2.write_bytes(b"hello   \nworld  \n")
        assert canonical_sha256_file(f1) == canonical_sha256_file(f2)

    def test_final_newline_normalized(self, tmp_path: Path):
        f1 = tmp_path / "newline.md"
        f2 = tmp_path / "no_newline.md"
        f1.write_bytes(b"hello\n")
        f2.write_bytes(b"hello")
        assert canonical_sha256_file(f1) == canonical_sha256_file(f2)

    def test_nfc_nfd_same_hash(self, tmp_path: Path):
        # é as NFC (single codepoint) vs NFD (e + combining accent)
        nfc = tmp_path / "nfc.md"
        nfd = tmp_path / "nfd.md"
        nfc.write_text("café\n", encoding="utf-8")
        nfd_bytes = "café\n".encode("utf-8")
        nfd.write_bytes(nfd_bytes)
        assert canonical_sha256_file(nfc) == canonical_sha256_file(nfd)

    def test_crlf_plus_nfd_same_as_lf_nfc(self, tmp_path: Path):
        f1 = tmp_path / "clean.md"
        f2 = tmp_path / "messy.md"
        f1.write_text("café\n", encoding="utf-8")
        f2.write_bytes("café\r\n".encode("utf-8"))
        assert canonical_sha256_file(f1) == canonical_sha256_file(f2)

    def test_different_content_different_hash(self, tmp_path: Path):
        f1 = tmp_path / "a.md"
        f2 = tmp_path / "b.md"
        f1.write_bytes(b"hello\n")
        f2.write_bytes(b"world\n")
        assert canonical_sha256_file(f1) != canonical_sha256_file(f2)

    def test_canonicalize_text_string(self):
        result = canonicalize_text_string("hello  \r\n  world  \r\n")
        # rstrip strips trailing whitespace per line, not leading
        assert result == "hello\n  world\n"


class TestJsonCanonicalization:
    def test_json_key_order_irrelevant(self, tmp_path: Path):
        f1 = tmp_path / "a.json"
        f2 = tmp_path / "b.json"
        f1.write_text('{"a": 1, "b": 2}', encoding="utf-8")
        f2.write_text('{"b": 2, "a": 1}', encoding="utf-8")
        assert canonical_sha256_file(f1) == canonical_sha256_file(f2)

    def test_json_pretty_compact_same(self, tmp_path: Path):
        f1 = tmp_path / "compact.json"
        f2 = tmp_path / "pretty.json"
        f1.write_text('{"a":1}', encoding="utf-8")
        f2.write_text('{\n  "a": 1\n}', encoding="utf-8")
        assert canonical_sha256_file(f1) == canonical_sha256_file(f2)

    def test_json_different_values_different_hash(self, tmp_path: Path):
        f1 = tmp_path / "a.json"
        f2 = tmp_path / "b.json"
        f1.write_text('{"a": 1}', encoding="utf-8")
        f2.write_text('{"a": 2}', encoding="utf-8")
        assert canonical_sha256_file(f1) != canonical_sha256_file(f2)


class TestFloatRejection:
    def test_integer_passes(self):
        reject_float_values({"a": 1, "b": [2, 3]})

    def test_string_passes(self):
        reject_float_values({"confidence": "high"})

    def test_float_rejected(self):
        with pytest.raises(ValueError, match="JSON_FLOAT_NOT_ALLOWED"):
            reject_float_values({"confidence": 0.8})

    def test_nested_float_rejected(self):
        with pytest.raises(ValueError, match="JSON_FLOAT_NOT_ALLOWED"):
            reject_float_values({"data": {"score": 1.5}})

    def test_float_in_list_rejected(self):
        with pytest.raises(ValueError, match="JSON_FLOAT_NOT_ALLOWED"):
            reject_float_values({"items": [1, 2.0, 3]})

    def test_scientific_notation_rejected(self):
        with pytest.raises(ValueError, match="JSON_FLOAT_NOT_ALLOWED"):
            reject_float_values({"val": 1e-3})

    def test_json_canonical_rejects_float(self, tmp_path: Path):
        f = tmp_path / "float.json"
        f.write_text('{"a": 1.0}', encoding="utf-8")
        with pytest.raises(ValueError, match="JSON_FLOAT_NOT_ALLOWED"):
            canonical_sha256_file(f)


class TestHashScopeMatrix:
    def test_draft_is_text_canonical(self):
        assert get_hash_strategy_for_source("arcs/arc_001/drafts/ch_001.md") == HashStrategy.TEXT_CANONICAL

    def test_outline_is_text_canonical(self):
        assert get_hash_strategy_for_source("canon/approved_outline.md") == HashStrategy.TEXT_CANONICAL

    def test_ledger_is_json_canonical(self):
        assert get_hash_strategy_for_source("ledgers/timeline.json") == HashStrategy.JSON_CANONICAL

    def test_aws_is_json_canonical(self):
        assert get_hash_strategy_for_source("arcs/arc_001/arc_working_state.json") == HashStrategy.JSON_CANONICAL

    def test_summary_is_json_canonical(self):
        assert get_hash_strategy_for_source("workspace/summaries/ch_001_summary.json") == HashStrategy.JSON_CANONICAL

    def test_metrics_is_not_hashed(self):
        assert get_hash_strategy_for_source("workspace/metrics.jsonl") == HashStrategy.NOT_HASHED

    def test_traces_is_not_hashed(self):
        assert get_hash_strategy_for_source("workspace/retrieval_traces/ch_001.jsonl") == HashStrategy.NOT_HASHED

    def test_reports_is_not_hashed(self):
        assert get_hash_strategy_for_source("workspace/reports/arc_health_report.md") == HashStrategy.NOT_HASHED

    def test_phase2_is_not_hashed(self):
        assert get_hash_strategy_for_source("workspace/phase2/meta.json") == HashStrategy.NOT_HASHED

    def test_unknown_ext_is_raw(self):
        assert get_hash_strategy_for_source("data.bin") == HashStrategy.RAW_SHA256
