"""MCP Server — Phase 3 G-05, G-06.

Exposes Novel Workflow capabilities via MCP (Model Context Protocol).
Two tool tiers:
  - Only-read: query chapters, retrieval traces, governance, jobs
  - Propose-only: create proposal (NEVER apply)

Security:
  - No apply, no gate approve, no snapshot promotion
  - External agents CANNOT modify canon/ledgers
  - All writes go through proposal → human gate path
"""

import json
import os
import sys
from pathlib import Path
from typing import Any


class MCPServer:
    """Minimal MCP-compatible JSON-RPC server.

    Implements the MCP protocol subset needed for novel-workflow tools.
    """

    def __init__(self, project_root: Path):
        self._root = project_root

    # ================================================================
    # Read-only tools (G-05)
    # ================================================================

    def list_tools(self) -> list[dict]:
        """List available MCP tools."""
        return [
            {
                "name": "query_chapters",
                "description": "Query chapter content and metadata. Read-only.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "chapter_id": {"type": "string", "description": "Chapter ID, e.g. ch_003"},
                        "query": {"type": "string", "description": "Search query for BM25 retrieval"},
                    },
                },
            },
            {
                "name": "get_retrieval_trace",
                "description": "Get retrieval trace for a chapter. Read-only.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "chapter_id": {"type": "string"},
                    },
                    "required": ["chapter_id"],
                },
            },
            {
                "name": "get_governance_report",
                "description": "Get governance report for a chapter. Read-only.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "chapter_id": {"type": "string"},
                    },
                    "required": ["chapter_id"],
                },
            },
            {
                "name": "get_job_status",
                "description": "Get outbox job status. Read-only.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "job_id": {"type": "string"},
                    },
                },
            },
            {
                "name": "get_chapter_commits",
                "description": "Get chapter commit history. Read-only.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 20},
                    },
                },
            },
            {
                "name": "create_proposal",
                "description": "Create a ledger update proposal. Propose-only — does NOT apply. "
                               "Proposal goes to human gate for approval.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "arc_id": {"type": "string"},
                        "target_ledger": {"type": "string"},
                        "operation": {"type": "string"},
                        "data": {"type": "object"},
                        "evidence": {"type": "string"},
                    },
                    "required": ["arc_id", "target_ledger", "operation", "data"],
                },
            },
        ]

    # --- Tool implementations ---

    def query_chapters(self, chapter_id: str = "", query: str = "") -> dict:
        """Query chapters by ID or search query."""
        result = {"chapters": [], "search_results": []}

        # Direct chapter lookup
        if chapter_id:
            ch_path = self._root / "canon" / "manuscript" / f"{chapter_id}.md"
            if ch_path.exists():
                content = ch_path.read_text(encoding="utf-8")
                result["chapters"].append({
                    "chapter_id": chapter_id,
                    "content_preview": content[:500],
                    "char_count": len(content),
                })

        # BM25 search
        if query:
            try:
                from novel_workflow.system_scripts.bm25_retriever import BM25Retriever
                bm25 = BM25Retriever(self._root)
                if bm25.exists():
                    matches = bm25.search(query, top_k=5)
                    for m in matches:
                        result["search_results"].append({
                            "item_id": m.item_id,
                            "item_type": m.item_type,
                            "content_preview": m.content[:300],
                            "score": m.score,
                            "chapter_id": m.chapter_id,
                        })
            except Exception as e:
                result["search_error"] = str(e)

        return result

    def get_retrieval_trace(self, chapter_id: str) -> dict:
        """Get retrieval trace from workspace."""
        trace_path = self._root / "workspace" / "retrieval_traces" / f"{chapter_id}.jsonl"
        if not trace_path.exists():
            return {"error": "No trace found", "chapter_id": chapter_id}

        traces = []
        try:
            for line in trace_path.read_text(encoding="utf-8").strip().split("\n"):
                if line.strip():
                    traces.append(json.loads(line))
        except Exception:
            pass

        return {
            "chapter_id": chapter_id,
            "trace_count": len(traces),
            "traces": traces[-3:],  # Last 3 traces
        }

    def get_governance_report(self, chapter_id: str) -> dict:
        """Get governance report."""
        report_path = self._root / "workspace" / "reports" / f"governance_{chapter_id}.json"
        if not report_path.exists():
            return {"error": "No report found", "chapter_id": chapter_id}

        return json.loads(report_path.read_text(encoding="utf-8"))

    def get_job_status(self, job_id: str = "") -> dict:
        """Get outbox job statistics."""
        try:
            from novel_workflow.system_scripts.outbox_store import OutboxStore
            store = OutboxStore(self._root)
            store.initialize()

            if job_id:
                # Query specific job
                pass  # OutboxStore doesn't have single-job lookup, use stats

            return store.get_stats()
        except Exception as e:
            return {"error": str(e)}

    def get_chapter_commits(self, limit: int = 20) -> dict:
        """Get recent chapter commits."""
        try:
            from novel_workflow.schemas.chapter_commit import ChapterCommitStore
            store = ChapterCommitStore(self._root)
            log = store.load_all()
            recent = log.commits[-limit:]
            return {
                "total_commits": len(log.commits),
                "recent": [
                    {
                        "commit_id": c.commit_id,
                        "chapter_id": c.chapter_id,
                        "arc_id": c.arc_id,
                        "applied_at": c.applied_at,
                        "trace_id": c.trace_id,
                    }
                    for c in recent
                ],
            }
        except Exception as e:
            return {"error": str(e)}

    # ================================================================
    # Propose-only tool (G-06)
    # ================================================================

    def create_proposal(
        self,
        arc_id: str,
        target_ledger: str,
        operation: str,
        data: dict,
        evidence: str = "",
        source_artifact: str = "",
    ) -> dict:
        """Create a ledger update proposal. Propose-only — NEVER applies.

        The proposal is written to arcs/<arc_id>/proposals/ and requires
        human gate approval before it can be applied.
        """
        from novel_workflow.schemas.proposal import LedgerUpdateProposal

        # Validate operation
        from novel_workflow.config import LEDGER_OPERATIONS
        allowed_ops = LEDGER_OPERATIONS.get(target_ledger, set())
        if operation not in allowed_ops:
            return {
                "error": f"Invalid operation '{operation}' for ledger '{target_ledger}'",
                "allowed_operations": list(allowed_ops),
            }

        # Create proposal
        proposal = LedgerUpdateProposal(
            claim=f"MCP proposal: {operation} on {target_ledger}",
            source_layer="draft",
            source_artifact=source_artifact or f"arcs/{arc_id}/drafts/latest.md",
            evidence=evidence or "MCP proposal from external agent",
            confidence="medium",
            target_ledger=target_ledger,
            operation=operation,
            proposed_change=data,
        )

        # Write to proposals directory
        proposals_dir = self._root / "arcs" / arc_id / "proposals"
        proposals_dir.mkdir(parents=True, exist_ok=True)

        import time
        proposal_id = f"proposal_mcp_{int(time.time())}"
        proposal_path = proposals_dir / f"{proposal_id}.json"
        proposal_path.write_text(
            proposal.model_dump_json(indent=2),
            encoding="utf-8",
        )

        return {
            "status": "proposed",
            "proposal_id": proposal_id,
            "proposal_path": str(proposal_path.relative_to(self._root)),
            "target_ledger": target_ledger,
            "operation": operation,
            "message": "Proposal created. Requires human gate approval before apply.",
            "next_step": "Awaiting human gate approval",
        }

    # ================================================================
    # MCP stdio protocol
    # ================================================================

    def handle_request(self, request: dict) -> dict:
        """Handle a JSON-RPC request."""
        method = request.get("method", "")
        req_id = request.get("id")

        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": self.list_tools()}}

        if method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})

            handler = getattr(self, tool_name, None)
            if handler is None:
                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}}

            try:
                result = handler(**arguments)
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}]}}
            except Exception as e:
                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32603, "message": str(e)}}

        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}

    def run_stdio(self):
        """Run MCP server over stdio (JSON-RPC)."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = self.handle_request(request)
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
            except json.JSONDecodeError:
                sys.stdout.write(json.dumps({
                    "jsonrpc": "2.0", "id": None,
                    "error": {"code": -32700, "message": "Parse error"}
                }) + "\n")
                sys.stdout.flush()


def main():
    """Entry point for MCP server."""
    root = Path(os.environ.get("NOVEL_PROJECT_ROOT", "."))
    server = MCPServer(root)
    server.run_stdio()


if __name__ == "__main__":
    main()
