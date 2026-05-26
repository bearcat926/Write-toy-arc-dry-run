"""
LLM-driven 3-chapter toy arc dry run.
Uses NovelFlow function (no CrewAI Flow, direct orchestration).
"""
import json
import os
import sys
from pathlib import Path

# Set API key
os.environ["OPENAI_API_KEY"] = "REDACTED_API_KEY"

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from novel_workflow.project_init import init_project
from novel_workflow.crewai.flow import run_novel_flow


def setup_project(root: Path):
    """Initialize a toy project with canon and ledgers."""
    init_project(root)

    # Create canon state
    (root / "canon" / "canon_state.json").write_text(json.dumps({
        "schema_version": "1.0",
        "setting": "A medieval fantasy world where magic is rare and feared",
        "protagonist": "Kael, a young blacksmith's apprentice who dreams of adventure",
    }, indent=2))

    # Create approved outline
    (root / "canon" / "approved_outline.md").write_text("""# The Blacksmith's Apprentice

## Genre
Medieval Fantasy / Young Adult

## Core Theme
An ordinary person discovers extraordinary courage when faced with impossible choices.

## Arc 1: The Call
- ch_001: Kael's ordinary life in the village of Millhaven
- ch_002: A mysterious stranger arrives with a warning
- ch_003: Kael must choose between safety and duty

## Characters
- **Kael**: 17, blacksmith's apprentice, brave but inexperienced
- **Maren**: Village healer, Kael's childhood friend
- **The Stranger**: Hooded figure who knows more than they reveal
- **Blacksmith (Torren)**: Kael's master, protective but hiding a secret

## Hard Requirements
- Kael must make at least one meaningful choice that changes the story
- The world's magic rules must be established through showing, not telling

## Absolute Prohibition
- Kael must not die
- No modern technology or language
""")

    # Create ledgers
    (root / "ledgers" / "timeline.json").write_text(json.dumps({
        "schema_version": "1.0",
        "events": [],
    }, indent=2))

    (root / "ledgers" / "character_knowledge.json").write_text(json.dumps({
        "schema_version": "1.0",
        "character_knowledge_entries": [],
    }, indent=2))

    (root / "ledgers" / "foreshadowing.json").write_text(json.dumps({
        "schema_version": "1.0",
        "foreshadowing_entries": [],
    }, indent=2))

    print(f"Project initialized at {root}")


def verify_results(root: Path):
    """Verify all expected artifacts exist."""
    print("\n" + "="*60)
    print("Verifying results...")
    print("="*60 + "\n")

    # Check canon/manuscript
    manuscript = root / "canon" / "manuscript"
    if manuscript.exists():
        chapters = list(manuscript.glob("ch_*.md"))
        print(f"canon/manuscript: {len(chapters)} chapters")
        for ch in sorted(chapters):
            content = ch.read_text(encoding="utf-8", errors="replace")
            print(f"  {ch.name}: {len(content)} chars")
    else:
        print("WARNING: canon/manuscript/ missing")

    # Check ledgers
    for ledger_file in (root / "ledgers").glob("*.json"):
        data = json.loads(ledger_file.read_text(encoding="utf-8"))
        entries = data.get("events", data.get("timeline_entries",
                        data.get("character_knowledge_entries",
                        data.get("foreshadowing_entries", []))))
        print(f"{ledger_file.name}: {len(entries)} entries")

    # Check apply record
    apply_record = root / "arcs" / "arc_001" / "reports" / "apply_record.json"
    if apply_record.exists():
        record = json.loads(apply_record.read_text(encoding="utf-8"))
        print(f"Apply record: {record.get('result')}")
    else:
        print("WARNING: No apply record found")


if __name__ == "__main__":
    root = (Path(__file__).parent / "toy_project_llm").resolve()
    setup_project(root)

    print("\n" + "="*60)
    print("Starting NovelFlow with real LLM...")
    print("="*60 + "\n")

    result = run_novel_flow(
        project_root=str(root),
        arc_id="arc_001",
        chapters_total=3,
    )

    verify_results(root)
