"""Tests for MCP Server (Phase 3 G-05, G-06)."""

import json
import tempfile
from pathlib import Path

import pytest

from novel_workflow.system_scripts.mcp_server import MCPServer


@pytest.fixture
def server():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "canon" / "manuscript").mkdir(parents=True)
        (root / "ledgers").mkdir(parents=True)
        (root / "workspace" / "reports").mkdir(parents=True)
        (root / "arcs" / "test_arc" / "proposals").mkdir(parents=True)

        (root / "canon" / "manuscript" / "ch_001.md").write_text("# Chapter 1\n\nTest content.", encoding="utf-8")

        yield MCPServer(root)


class TestMCPTools:
    def test_list_tools(self, server):
        tools = server.list_tools()
        assert len(tools) > 0
        tool_names = [t["name"] for t in tools]
        assert "query_chapters" in tool_names
        assert "create_proposal" in tool_names

    def test_query_chapters(self, server):
        result = server.query_chapters(chapter_id="ch_001")
        assert len(result["chapters"]) == 1
        assert result["chapters"][0]["char_count"] > 0

    def test_get_retrieval_trace_empty(self, server):
        result = server.get_retrieval_trace("ch_001")
        assert "error" in result or result["trace_count"] == 0

    def test_get_governance_report_empty(self, server):
        result = server.get_governance_report("ch_001")
        assert "error" in result

    def test_get_job_status(self, server):
        result = server.get_job_status()
        assert "total_jobs" in result or "error" in result

    def test_get_chapter_commits_empty(self, server):
        result = server.get_chapter_commits()
        assert "total_commits" in result
        assert result["total_commits"] == 0

    def test_create_proposal(self, server):
        result = server.create_proposal(
            arc_id="test_arc",
            target_ledger="timeline",
            operation="append_event",
            data={"event_id": "evt_test", "description": "MCP test"},
            evidence="MCP test evidence",
        )
        assert result["status"] == "proposed"
        assert "proposal_id" in result

    def test_create_proposal_invalid_operation(self, server):
        result = server.create_proposal(
            arc_id="test_arc",
            target_ledger="timeline",
            operation="nonexistent_op",
            data={},
        )
        assert "error" in result

    def test_create_proposal_propose_only(self, server):
        """G-06: Propose-only — never auto-applies."""
        result = server.create_proposal(
            arc_id="test_arc",
            target_ledger="character_knowledge",
            operation="append_knowledge",
            data={"character_name": "Test", "knowledge": "test"},
        )
        assert result["status"] == "proposed"
        assert "next_step" in result
        assert "Awaiting human gate" in result.get("message", "") or "next_step" in result


class TestMCPProtocol:
    def test_handle_tools_list(self, server):
        req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        resp = server.handle_request(req)
        assert resp["id"] == 1
        assert "tools" in resp["result"]

    def test_handle_tools_call(self, server):
        req = {
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "query_chapters", "arguments": {"chapter_id": "ch_001"}},
        }
        resp = server.handle_request(req)
        assert resp["id"] == 2
        assert "content" in resp["result"]

    def test_handle_unknown_method(self, server):
        req = {"jsonrpc": "2.0", "id": 3, "method": "unknown"}
        resp = server.handle_request(req)
        assert "error" in resp

    def test_handle_unknown_tool(self, server):
        req = {
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "nonexistent_tool", "arguments": {}},
        }
        resp = server.handle_request(req)
        assert "error" in resp
