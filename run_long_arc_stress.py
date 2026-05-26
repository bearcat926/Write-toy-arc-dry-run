"""
Long arc stress test - 10 chapter arc with 3-5 characters, foreshadowing, POV switching.
Requires OPENAI_API_KEY environment variable.

Usage:
    export OPENAI_API_KEY="your-key"
    export OPENAI_API_BASE="https://your-endpoint/v1"
    export OPENAI_MODEL_NAME="your-model"
    python run_long_arc_stress.py
"""
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from novel_workflow.project_init import init_project
from novel_workflow.crewai.flow import run_novel_flow
from novel_workflow.metrics.collector import MetricsCollector


def setup_stress_project(root: Path):
    """Initialize a stress test project with richer content."""
    init_project(root)

    # Canon state
    (root / "canon" / "canon_state.json").write_text(json.dumps({
        "schema_version": "1.0",
        "setting": "A sprawling fantasy kingdom with multiple factions vying for control of ancient magic",
        "protagonist": "Kael, a blacksmith's apprentice who discovers he can hear the whispers of enchanted steel",
        "characters": {
            "kael": {"role": "protagonist", "age": 17, "trait": "brave but inexperienced"},
            "maren": {"role": "deuteragonist", "age": 19, "trait": "brilliant healer with a secret past"},
            "torren": {"role": "mentor", "age": 45, "trait": "master blacksmith hiding forbidden knowledge"},
            "voss": {"role": "antagonist", "age": 35, "trait": "ruthless magic collector"},
            "liora": {"role": "ally", "age": 22, "trait": "nomadic scout with loyalty conflicts"},
        },
    }, indent=2))

    # Approved outline
    (root / "canon" / "approved_outline.md").write_text("""# The Whispering Steel

## Genre
Epic Fantasy / Young Adult

## Core Theme
Power corrupts, but knowledge of one's limits protects.

## Arc 1: The Awakening (10 chapters)
- ch_001: Kael discovers he can hear enchanted steel at Torren's forge
- ch_002: Maren arrives with a wounded traveler carrying a strange blade
- ch_003: Torren reveals fragments of the ancient smithing tradition
- ch_004: Voss's agents arrive in Millhaven asking questions
- ch_005: Kael and Maren flee with the enchanted blade
- ch_006: Liora joins them as a guide through the wilderness
- ch_007: A betrayal reveals someone has been tracking them
- ch_008: Kael forges his first enchanted weapon
- ch_009: Confrontation with Voss's lieutenant
- ch_010: The truth about Torren's past changes everything

## Hard Requirements
- Kael must make at least one meaningful choice per chapter
- The magic system (enchanted steel whispers) must be consistently applied
- Foreshadowing: the broken sword (ch_001) must pay off by ch_010

## Absolute Prohibitions
- Kael must not die
- No modern technology or language
- No deus ex machina magic solutions

## POV Rules
- Primary POV: Kael (7 chapters)
- Secondary POV: Maren (3 chapters, ch_002, ch_007, ch_009)
- No character knows information outside their POV without explicit source
""", encoding="utf-8")

    # Ledgers
    for ledger, structure in [
        ("timeline.json", {"events": []}),
        ("character_knowledge.json", {"character_knowledge_entries": []}),
        ("foreshadowing.json", {"foreshadowing_entries": []}),
    ]:
        (root / "ledgers" / ledger).write_text(
            json.dumps({"schema_version": "1.0", **structure}, indent=2),
            encoding="utf-8",
        )

    print(f"Stress project initialized at {root}")


def run_stress_test():
    """Run 10-chapter stress test."""
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set. Export it before running.")
        print("  export OPENAI_API_KEY='your-key'")
        print("  export OPENAI_API_BASE='https://your-endpoint/v1'")
        print("  export OPENAI_MODEL_NAME='your-model'")
        sys.exit(1)

    root = (Path(__file__).parent / "toy_project_stress").resolve()
    setup_stress_project(root)

    print("\n" + "="*60)
    print("Starting 10-chapter stress test...")
    print("="*60 + "\n")

    result = run_novel_flow(
        project_root=str(root),
        arc_id="arc_001",
        chapters_total=10,
        dry_run=True,
    )

    # Generate metrics report
    collector = MetricsCollector(root)
    try:
        report = collector.generate_report("arc_001")
        print("\n" + "="*60)
        print("METRICS REPORT")
        print("="*60)
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


if __name__ == "__main__":
    run_stress_test()
