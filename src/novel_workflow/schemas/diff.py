from pydantic import BaseModel
from .common import SchemaVersioned, Timestamped


class LedgerDiff(SchemaVersioned, Timestamped):
    arc_id: str
    operations: list[dict]


class CanonDiff(SchemaVersioned, Timestamped):
    arc_id: str
    character_updates: list[dict] = []


class ApplyRecord(SchemaVersioned, Timestamped):
    arc_id: str
    ledger_diff_hash: str
    canon_diff_hash: str = ""
    result: str  # "success" | "rolled_back"
