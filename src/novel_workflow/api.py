"""Workbench API — Phase 3 H-01.

FastAPI backend for the Author Workbench. Provides read-only endpoints
for all workspace views and controlled write endpoints for the chapter
delivery desk.

Security: UI NEVER directly accesses canon/ledgers. All writes go through
the proposal → gate → apply pipeline.
"""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel


app = FastAPI(title="Novel Workflow Workbench", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PROJECT_ROOT = Path(".")


def set_project_root(path: Path):
    global PROJECT_ROOT
    PROJECT_ROOT = path


# ================================================================
# Models
# ================================================================

class ChapterListItem(BaseModel):
    chapter_id: str
    status: str = "draft"
    char_count: int = 0

class ApplyRequest(BaseModel):
    arc_id: str
    chapter_id: str
    author_evidence: str

class RollbackRequest(BaseModel):
    arc_id: str
    chapter_id: str


# ================================================================
# H-02: Book Workspace — overview
# ================================================================

@app.get("/api/workspace/overview")
async def get_overview():
    """Get project overview: chapters, arcs, system health."""
    manuscript_dir = PROJECT_ROOT / "canon" / "manuscript"
    chapters = []
    if manuscript_dir.exists():
        for ch in sorted(manuscript_dir.glob("ch_*.md")):
            content = ch.read_text(encoding="utf-8")
            chapters.append({
                "chapter_id": ch.stem,
                "char_count": len(content),
                "preview": content[:200],
            })

    # Arc info
    arcs = []
    arcs_dir = PROJECT_ROOT / "arcs"
    if arcs_dir.exists():
        for arc in sorted(arcs_dir.iterdir()):
            if arc.is_dir():
                drafts = len(list((arc / "drafts").glob("ch_*.md")))
                proposals = len(list((arc / "proposals").glob("*.json")))
                gates = len(list((arc / "gates").glob("*.json")))
                arcs.append({
                    "arc_id": arc.name,
                    "drafts": drafts,
                    "proposals": proposals,
                    "gates": gates,
                })

    # Commit log
    commit_count = 0
    try:
        from novel_workflow.schemas.chapter_commit import ChapterCommitStore
        store = ChapterCommitStore(PROJECT_ROOT)
        commit_count = store.count
    except Exception:
        pass

    # Outbox stats
    job_stats = {}
    try:
        from novel_workflow.system_scripts.outbox_store import OutboxStore
        os_store = OutboxStore(PROJECT_ROOT)
        os_store.initialize()
        job_stats = os_store.get_stats()
    except Exception:
        pass

    return {
        "chapters": chapters,
        "arcs": arcs,
        "total_chapters": len(chapters),
        "total_commits": commit_count,
        "outbox": job_stats,
    }


# ================================================================
# H-03: Chapter Delivery Desk
# ================================================================

@app.get("/api/chapters/{chapter_id}")
async def get_chapter(chapter_id: str):
    """Get chapter content and metadata."""
    ch_path = PROJECT_ROOT / "canon" / "manuscript" / f"{chapter_id}.md"
    if not ch_path.exists():
        raise HTTPException(404, f"Chapter {chapter_id} not found")

    content = ch_path.read_text(encoding="utf-8")

    # Get related artifacts
    summary_path = PROJECT_ROOT / "workspace" / "summaries" / f"{chapter_id}_summary.json"
    summary = None
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))

    audit_path = PROJECT_ROOT / "workspace" / "reports" / f"governance_{chapter_id}.json"
    audit = None
    if audit_path.exists():
        audit = json.loads(audit_path.read_text(encoding="utf-8"))

    return {
        "chapter_id": chapter_id,
        "content": content,
        "char_count": len(content),
        "summary": summary,
        "governance": audit,
    }


@app.post("/api/chapters/{chapter_id}/apply")
async def apply_chapter(chapter_id: str, req: ApplyRequest):
    """Apply a chapter (creates gate + applies)."""
    from novel_workflow.system_scripts.atomic_apply_manager import AtomicApplyManager
    from novel_workflow.schemas.gate import GateRecord
    from novel_workflow.schemas.diff import LedgerDiff

    mgr = AtomicApplyManager(PROJECT_ROOT)

    gate = GateRecord(
        gate_id=f"gate_wb_{chapter_id}",
        gate_type="arc_end",
        target_artifact=f"arcs/{req.arc_id}/drafts/{chapter_id}.md",
        decision="approved",
        author_input_evidence=req.author_evidence,
        author_id="workbench_user",
        source_artifacts=[f"arcs/{req.arc_id}/drafts/{chapter_id}.md"],
    )

    diff = LedgerDiff(
        arc_id=req.arc_id,
        operations=[{
            "target_ledger": "timeline",
            "operation": "append_event",
            "source_artifact": f"arcs/{req.arc_id}/drafts/{chapter_id}.md",
            "data": {
                "event_id": f"evt_wb_{chapter_id}",
                "event_type": "chapter_written",
                "chapter": chapter_id,
                "description": f"Workbench apply: {chapter_id}",
            },
        }],
    )

    result = mgr.apply(
        arc_id=req.arc_id,
        gate_record=gate,
        draft_files=[f"{chapter_id}.md"],
        ledger_diff=diff,
        canon_diff=None,
        dry_run=False,
    )

    return {"status": "applied", **result}


# ================================================================
# H-04: Narrative Health
# ================================================================

@app.get("/api/health")
async def get_health():
    """Get narrative health overview."""
    reports = []
    reports_dir = PROJECT_ROOT / "workspace" / "reports"
    if reports_dir.exists():
        for r in sorted(reports_dir.glob("governance_ch_*.json")):
            try:
                data = json.loads(r.read_text(encoding="utf-8"))
                reports.append({
                    "chapter_id": data.get("chapter_id", r.stem),
                    "warning_count": data.get("warning_count", 0),
                    "max_severity": data.get("max_severity", "none"),
                    "recommended_action": data.get("recommended_action", "approve"),
                })
            except Exception:
                pass

    return {"reports": reports, "total_reports": len(reports)}


# ================================================================
# H-05: Retrieval Trace
# ================================================================

@app.get("/api/traces/{chapter_id}")
async def get_trace(chapter_id: str):
    """Get retrieval trace for a chapter."""
    trace_path = PROJECT_ROOT / "workspace" / "retrieval_traces" / f"{chapter_id}.jsonl"
    if not trace_path.exists():
        return {"chapter_id": chapter_id, "traces": []}

    traces = []
    for line in trace_path.read_text(encoding="utf-8").strip().split("\n"):
        if line.strip():
            try:
                traces.append(json.loads(line))
            except Exception:
                pass

    return {"chapter_id": chapter_id, "traces": traces}


# ================================================================
# H-06: Job Monitor
# ================================================================

@app.get("/api/jobs")
async def get_jobs():
    """Get outbox job status."""
    try:
        from novel_workflow.system_scripts.outbox_store import OutboxStore
        store = OutboxStore(PROJECT_ROOT)
        store.initialize()

        return {
            "stats": store.get_stats(),
            "pending": [j.to_dict() for j in store.get_pending(limit=10)],
            "running": [j.to_dict() for j in store.get_running()],
            "dead": [j.to_dict() for j in store.get_dead_letter(limit=10)],
        }
    except Exception as e:
        return {"error": str(e)}


# ================================================================
# H-07: Rollback
# ================================================================

@app.post("/api/chapters/{chapter_id}/rollback")
async def rollback_chapter(chapter_id: str, req: RollbackRequest):
    """Rollback a chapter (mark snapshot as stale)."""
    from novel_workflow.system_scripts.stable_generation_pointer import StableGenerationPointer

    pointer = StableGenerationPointer(PROJECT_ROOT)

    # Find the artifact to rollback
    entry = pointer.get_stable(f"chapter:{chapter_id}")
    if entry is None:
        raise HTTPException(404, f"No stable entry for chapter {chapter_id}")

    result = pointer.rollback_to_previous(f"chapter:{chapter_id}")
    return {"status": "rolled_back" if result else "not_found"}


# ================================================================
# Workbench HTML (embedded)
# ================================================================

@app.get("/")
async def workbench():
    """Serve the workbench HTML."""
    html_path = Path(__file__).parent.parent.parent / "tools" / "workbench.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Workbench not found</h1>")


def main():
    import uvicorn
    import sys
    if len(sys.argv) > 1:
        set_project_root(Path(sys.argv[1]))
    uvicorn.run(app, host="127.0.0.1", port=8765)


if __name__ == "__main__":
    main()
