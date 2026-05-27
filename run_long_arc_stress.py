"""
Long arc stress test - modular version.
Runs in batches of 3 chapters to avoid LLM timeout.
Usage:
    export OPENAI_API_KEY=... OPENAI_API_BASE=... OPENAI_MODEL_NAME=...
    python run_long_arc_stress.py           # run all 10 chapters
    python run_long_arc_stress.py --batch 3 # run chapters 1-3 only
"""
import json
import os
import sys
import argparse
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from novel_workflow.project_init import init_project
from novel_workflow.crewai.flow import run_novel_flow
from novel_workflow.metrics.collector import MetricsCollector


def setup_stress_project(root: Path):
    """Initialize stress test project."""
    init_project(root)
    (root / "canon" / "canon_state.json").write_text(json.dumps({
        "schema_version": "1.0",
        "setting": "A sprawling fantasy kingdom with multiple factions vying for control of ancient magic",
        "protagonist": "Kael, a blacksmith's apprentice who discovers he can hear enchanted steel",
    }, indent=2))

    (root / "canon" / "approved_outline.md").write_text("""# The Whispering Steel

## Genre: Epic Fantasy / YA

## Arc 1: The Awakening (10 chapters)
- ch_001: Kael hears enchanted steel at Torren's forge
- ch_002: Maren arrives with a wounded traveler
- ch_003: Torren reveals ancient smithing tradition
- ch_004: Voss's agents arrive in Millhaven
- ch_005: Kael and Maren flee with the blade
- ch_006: Liora joins as wilderness guide
- ch_007: A betrayal reveals tracking (Maren POV)
- ch_008: Kael forges his first weapon
- ch_009: Confrontation with Voss's lieutenant (Maren POV)
- ch_010: Torren's past changes everything

## Hard Requirements
- Kael makes meaningful choice each chapter
- Magic system consistency
- Foreshadowing: broken sword (ch_001) pays off by ch_010

## Absolute Prohibitions
- Kael must not die
- No modern technology
- No deus ex machina
""", encoding="utf-8")

    for ledger, structure in [
        ("timeline.json", {"events": []}),
        ("character_knowledge.json", {"character_knowledge_entries": []}),
        ("foreshadowing.json", {"foreshadowing_entries": []}),
    ]:
        (root / "ledgers" / ledger).write_text(
            json.dumps({"schema_version": "1.0", **structure}, indent=2), encoding="utf-8")

    print(f"Stress project initialized at {root}")


def run_stress_batch(root: Path, start_ch: int, end_ch: int) -> dict:
    """Run a batch of chapters."""
    chapters = end_ch - start_ch + 1
    print(f"\n{'='*60}")
    print(f"Running chapters {start_ch}-{end_ch} ({chapters} chapters)")
    print(f"{'='*60}\n")

    result = run_novel_flow(
        project_root=str(root),
        arc_id="arc_001",
        chapters_total=end_ch,
        start_ch=args.start,
        dry_run=True,
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=10, help="Number of chapters to run")
    parser.add_argument("--start", type=int, default=1, help="Start chapter")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: Set OPENAI_API_KEY, OPENAI_API_BASE, OPENAI_MODEL_NAME")
        sys.exit(1)

    root = (Path(__file__).parent / "toy_project_stress").resolve()

    # Only init if fresh
    if not (root / "canon" / "canon_state.json").exists():
        setup_stress_project(root)

    end_ch = args.start + args.batch - 1
    result = run_stress_batch(root, args.start, end_ch)

    # Metrics report
    collector = MetricsCollector(root)
    try:
        report = collector.generate_report("arc_001")
        print(f"\n{'='*60}")
        print("METRICS REPORT")
        print(f"{'='*60}")
        print(f"Chapters: {report.chapters_total}")
        print(f"Proposal accept rate: {report.proposal_accept_rate:.2%}")
        print(f"Audit fail rate: {report.audit_fail_rate:.2%}")
        print(f"Pause rate: {report.pause_rate:.2%}")
        print(f"Total retries: {report.total_retries}")
        print(f"Total runtime: {report.total_runtime_seconds:.1f}s")
        print(f"AWS entries: {report.aws_entry_count}")
        print(f"AWS file size: {report.aws_file_size_bytes} bytes")
    except ValueError as e:
        print(f"Metrics error: {e}")

    print(f"\nApply result: {result.get('apply_result')}")
