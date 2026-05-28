"""Canonical hash protocol for Phase 2 provenance.

Ensures cross-platform hash stability by normalizing:
- UTF-8 BOM removal
- Unicode NFC normalization
- CRLF/CR → LF
- Trailing whitespace per line
- Final newline normalization
- JSON: sort_keys, compact separators, no float values
"""
import hashlib
import json
import unicodedata
from pathlib import Path
from typing import Any

from ..schemas.enums import HashStrategy


def canonicalize_text_string(text: str) -> str:
    """Normalize text string for canonical hashing."""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines).rstrip("\n") + "\n"
    return text


def canonicalize_text_bytes(raw: bytes) -> bytes:
    """Decode UTF-8-sig and normalize for canonical hashing."""
    text = raw.decode("utf-8-sig")
    return canonicalize_text_string(text).encode("utf-8")


def reject_float_values(obj: Any, path: str = "$") -> None:
    """Reject non-integer floats in JSON structure."""
    if isinstance(obj, float):
        raise ValueError(f"JSON_FLOAT_NOT_ALLOWED:{path}")
    if isinstance(obj, dict):
        for k, v in obj.items():
            reject_float_values(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            reject_float_values(v, f"{path}[{i}]")


def canonicalize_json_for_hash(raw: bytes) -> bytes:
    """Normalize JSON for canonical hashing: parse, reject floats, sort, compact."""
    obj = json.loads(raw.decode("utf-8-sig"))
    reject_float_values(obj)
    canonical = json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return (canonical + "\n").encode("utf-8")


def canonical_sha256_file(path: Path) -> str:
    """Compute canonical SHA-256 hash of a file."""
    raw = path.read_bytes()
    if path.suffix == ".json":
        payload = canonicalize_json_for_hash(raw)
    else:
        payload = canonicalize_text_bytes(raw)
    return hashlib.sha256(payload).hexdigest()


def get_hash_strategy_for_source(path: str) -> HashStrategy:
    """Determine hash strategy for a source artifact path."""
    if path.startswith("workspace/metrics"):
        return HashStrategy.NOT_HASHED
    if path.startswith("workspace/retrieval_traces/"):
        return HashStrategy.NOT_HASHED
    if path.startswith("workspace/reports/"):
        return HashStrategy.NOT_HASHED
    if path.startswith("workspace/phase2/"):
        return HashStrategy.NOT_HASHED

    if path.endswith(".json"):
        return HashStrategy.JSON_CANONICAL
    if path.endswith((".md", ".txt")):
        return HashStrategy.TEXT_CANONICAL

    return HashStrategy.RAW_SHA256
