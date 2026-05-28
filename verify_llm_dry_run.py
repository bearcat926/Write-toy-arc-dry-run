"""
Automated LLM dry run verification script.
Runs NovelFlow and validates all expected artifacts exist.
"""
import json
import sys
from pathlib import Path

# Verify artifacts after dry run
def verify_dry_run(root: Path) -> tuple[bool, list[str]]:
    failures = []

    # 1. Check canon/manuscript has 3 chapters
    manuscript = root / "canon" / "manuscript"
    if not manuscript.exists():
        failures.append("canon/manuscript/ directory missing")
    else:
        chapters = list(manuscript.glob("ch_*.md"))
        if len(chapters) < 3:
            failures.append(f"Expected 3 chapters in canon/manuscript, found {len(chapters)}")

    # 2. Check ledgers updated
    for ledger in ["timeline", "character_knowledge", "foreshadowing"]:
        path = root / "ledgers" / f"{ledger}.json"
        if not path.exists():
            failures.append(f"Ledger {ledger}.json missing")
        else:
            data = json.loads(path.read_text(encoding="utf-8"))
            entries = data.get("events", data.get("timeline_entries",
                            data.get("character_knowledge_entries",
                            data.get("foreshadowing_entries", []))))
            if len(entries) == 0:
                failures.append(f"Ledger {ledger}.json has 0 entries")

    # 3. Check arc_working_state has entries
    aws_path = root / "arcs" / "arc_001" / "arc_working_state.json"
    if not aws_path.exists():
        failures.append("arc_working_state.json missing")
    else:
        aws = json.loads(aws_path.read_text(encoding="utf-8"))
        if len(aws.get("entries", [])) == 0:
            failures.append("arc_working_state has 0 entries")

    # 4. Check apply_record exists and has valid diff_hash
    apply_record = root / "arcs" / "arc_001" / "reports" / "apply_record.json"
    if not apply_record.exists():
        failures.append("apply_record.json missing")
    else:
        record = json.loads(apply_record.read_text(encoding="utf-8"))
        if record.get("result") != "success":
            failures.append(f"Apply record result: {record.get('result')}")
        if not record.get("ledger_diff_hash"):
            failures.append("apply_record.json has empty ledger_diff_hash")

    # 5. Check 3 gate files exist and are valid
    gates_dir = root / "arcs" / "arc_001" / "gates"
    expected_gates = ["direction_gate.json", "arc_start_gate.json", "arc_end_gate.json"]
    for gate_name in expected_gates:
        gate_path = gates_dir / gate_name
        if not gate_path.exists():
            failures.append(f"Gate file missing: {gate_name}")
        else:
            try:
                gate_data = json.loads(gate_path.read_text(encoding="utf-8"))
                if not gate_data.get("gate_id"):
                    failures.append(f"Gate {gate_name}: missing gate_id")
                if gate_data.get("schema_version") != "1.0":
                    failures.append(f"Gate {gate_name}: invalid schema_version")
            except json.JSONDecodeError:
                failures.append(f"Gate {gate_name}: invalid JSON")

    # 6. Check drafts exist
    drafts = root / "arcs" / "arc_001" / "drafts"
    if drafts.exists():
        draft_files = list(drafts.glob("ch_*.md"))
        if len(draft_files) < 3:
            failures.append(f"Expected 3 drafts, found {len(draft_files)}")

    return (len(failures) == 0, failures)


if __name__ == "__main__":
    root = Path(__file__).parent / "toy_project_llm"
    if not root.exists():
        print(f"ERROR: {root} does not exist. Run run_llm_dry_run.py first.")
        sys.exit(1)

    passed, failures = verify_dry_run(root)
    if passed:
        print("DRY RUN VERIFICATION: PASSED")
        print("All artifacts verified:")
        print(f"  - canon/manuscript: 3 chapters")
        print(f"  - ledgers: timeline, character_knowledge, foreshadowing updated")
        print(f"  - arc_working_state: entries present")
        print(f"  - apply_record: success")
        print(f"  - gates: direction, arc_start, arc_end")
    else:
        print("DRY RUN VERIFICATION: FAILED")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
