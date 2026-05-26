"""
LLM-driven 3-chapter toy arc dry run.
Runs NovelFlow with real LLM to verify the full pipeline.
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
from novel_workflow.crewai.flow import NovelFlow, NovelFlowState


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

    # Create arc directory
    arc_dir = root / "arcs" / "arc_001"
    for d in ["drafts", "reviews", "proposals", "reports", "gates", "checkpoints", "archive"]:
        (arc_dir / d).mkdir(parents=True, exist_ok=True)

    # Create gates directory
    (root / "gates").mkdir(parents=True, exist_ok=True)

    print(f"Project initialized at {root}")


def run_dry_run():
    """Run the full 3-chapter toy arc with real LLM."""
    root = Path(__file__).parent / "toy_project_llm"
    setup_project(root)

    print("\n" + "="*60)
    print("Starting NovelFlow with real LLM...")
    print("="*60 + "\n")

    state = NovelFlowState(
        arc_id="arc_001",
        chapters_total=3,
        project_root=str(root),
    )

    flow = NovelFlow(state=state)
    flow.kickoff()

    print("\n" + "="*60)
    print("NovelFlow complete! Checking results...")
    print("="*60 + "\n")

    # Verify results
    manuscript_dir = root / "canon" / "manuscript"
    if manuscript_dir.exists():
        for f in sorted(manuscript_dir.glob("*.md")):
            content = f.read_text()
            print(f"\n--- {f.name} ({len(content)} chars) ---")
            print(content[:200] + "..." if len(content) > 200 else content)

    # Check ledgers
    for ledger_file in (root / "ledgers").glob("*.json"):
        data = json.loads(ledger_file.read_text())
        entries = data.get("events", data.get("timeline_entries", data.get("character_knowledge_entries", data.get("foreshadowing_entries", []))))
        print(f"\n{ledger_file.name}: {len(entries)} entries")

    # Check apply record
    apply_record = root / "arcs" / "arc_001" / "reports" / "apply_record.json"
    if apply_record.exists():
        print(f"\nApply record: {apply_record.read_text()[:200]}")
    else:
        print("\nWARNING: No apply record found!")


if __name__ == "__main__":
    run_dry_run()
