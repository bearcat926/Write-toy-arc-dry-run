#!/usr/bin/env python3
"""100-Chapter LLM Stress Test — Phase 3 I-01 validated.

Uses real LLM API to generate coherent, arc-aware chapters.
Tracks per-chapter: tokens_in, tokens_out, context_size, latency.

API keys are read from C:/Users/18622/Desktop/key.txt as temp env vars.
Sensitive information is NEVER logged or displayed.

Usage:
    python scripts/run_stress_test.py --chapters 20 [--project-root tools/stress_llm_output]
"""

import argparse
import json
import os
import shutil
import sys
import time as _time
import hashlib
from pathlib import Path


# ================================================================
# API Config (from key.txt, never logged)
# ================================================================

def _load_keys() -> dict:
    key_file = Path("C:/Users/18622/Desktop/key.txt")
    env = {}
    if key_file.exists():
        for line in key_file.read_text(encoding="utf-8").strip().split("\n"):
            if "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


_key_env = _load_keys()

API_BASE = _key_env.get("OPENAI_API_BASE", "")
API_MODEL = _key_env.get("OPENAI_MODEL_NAME", "")
API_KEY = _key_env.get("OPENAI_API_KEY", "")


# ================================================================
# Chapter Generator — LLM-driven with context accumulation
# ================================================================

ARC_OUTLINE = """
You are writing a fantasy novel arc titled "The Obsidian Prophecy".
The story follows Kael, a warrior of the Sunstrider clan, who wields Dawnbreaker.
Accompanied by Lira (Elven scholar) and opposed by Marcus (Shadow Council commander).
Setting: A world divided between kingdoms Valdris, Eryndor, Thalassia, and Nordmark.
Central mystery: An ancient artifact known only as "the Obsidian Heart" that
can manipulate time — but at a terrible cost.

Write ONE chapter (300-600 words). Each chapter must:
1. Advance the plot in a meaningful way
2. Feature character development for at least one main character
3. End with a hook or turning point
4. Be self-contained enough to read as a single unit
5. Maintain continuity with previous events

Format: "# Chapter N: Title" followed by the chapter text. No meta-commentary.
"""


def build_context(chapter_num: int, history: list[dict]) -> str:
    """Build LLM context window from arc outline + chapter history."""
    context = ARC_OUTLINE.strip()

    # Add previous chapter summaries (sliding window)
    if history:
        summaries = []
        start = max(0, len(history) - 5)  # Last 5 chapters
        for h in history[start:]:
            title = h.get("title", f"Chapter {h['num']}")
            summary = h.get("content", "")[:300]
            if summary:
                summaries.append(f"Previously in {title}:\n{summary}...")
        if summaries:
            context += "\n\n--- PREVIOUS CHAPTERS ---\n" + "\n\n".join(summaries)

    context += f"\n\nNow write Chapter {chapter_num}."
    return context


def call_llm(prompt: str, max_tokens: int = 800) -> dict:
    """Call LLM with retry on 429/5xx/timeout. API key never logged.

    Retry strategy: exponential backoff [5s, 10s, 20s, 40s, 80s], max 5 attempts.
    On 429: wait Retry-After header or default backoff.
    """
    import os as _os
    _os.environ["OPENAI_API_KEY"] = API_KEY
    _os.environ["OPENAI_API_BASE"] = API_BASE
    _os.environ["OPENAI_MODEL_NAME"] = API_MODEL

    from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError, InternalServerError

    last_error = ""
    for attempt in range(5):
        try:
            t0 = _time.time()
            client = OpenAI(api_key=API_KEY, base_url=API_BASE, timeout=120.0)
            resp = client.chat.completions.create(
                model=API_MODEL,
                messages=[
                    {"role": "system", "content": "You are a fantasy novelist. Write ONE chapter only."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.8,
            )

            elapsed_ms = int((_time.time() - t0) * 1000)
            return {
                "content": resp.choices[0].message.content.strip() if resp.choices else "",
                "tokens_in": resp.usage.prompt_tokens if resp.usage else 0,
                "tokens_out": resp.usage.completion_tokens if resp.usage else 0,
                "total_tokens": (resp.usage.prompt_tokens + resp.usage.completion_tokens) if resp.usage else 0,
                "latency_ms": elapsed_ms,
                "finish_reason": resp.choices[0].finish_reason if resp.choices else "unknown",
            }

        except RateLimitError as e:
            last_error = f"429 rate limited (attempt {attempt+1}/5)"
            wait = min(5 * (2 ** attempt), 120)
            print(f"(429, retry in {wait}s)", end=" ", flush=True)
            _time.sleep(wait)
        except (APITimeoutError, APIConnectionError) as e:
            last_error = f"timeout/connection (attempt {attempt+1}/5)"
            wait = min(3 * (2 ** attempt), 60)
            print(f"(timeout, retry in {wait}s)", end=" ", flush=True)
            _time.sleep(wait)
        except InternalServerError as e:
            last_error = f"500 server error (attempt {attempt+1}/5)"
            wait = min(3 * (2 ** attempt), 60)
            print(f"(500, retry in {wait}s)", end=" ", flush=True)
            _time.sleep(wait)
        except Exception as e:
            err_str = str(e)[:80]
            if "429" in err_str or "rate" in err_str.lower():
                last_error = f"rate limited (attempt {attempt+1}/5)"
                wait = min(5 * (2 ** attempt), 120)
                print(f"(rate, retry in {wait}s)", end=" ", flush=True)
                _time.sleep(wait)
            elif any(x in err_str.lower() for x in ["timeout", "connect", "reset", "refused"]):
                last_error = f"network error (attempt {attempt+1}/5)"
                wait = min(3 * (2 ** attempt), 60)
                print(f"(net, retry in {wait}s)", end=" ", flush=True)
                _time.sleep(wait)
            else:
                # Non-retryable error
                elapsed_ms = int((_time.time() - t0) * 1000)
                return {
                    "content": "", "tokens_in": 0, "tokens_out": 0, "total_tokens": 0,
                    "latency_ms": elapsed_ms, "finish_reason": "error", "error": err_str,
                }

    # All retries exhausted
    elapsed_ms = int((_time.time() - t0) * 1000)
    return {
        "content": "", "tokens_in": 0, "tokens_out": 0, "total_tokens": 0,
        "latency_ms": elapsed_ms, "finish_reason": "retry_exhausted", "error": last_error,
    }


# ================================================================
# Stress Test Pipeline
# ================================================================

def setup_stress_project(root: Path, num_chapters: int) -> Path:
    """Initialize project directory structure."""
    arc_dir = root / "arcs" / "stress_arc"
    for sub in ["drafts", "reports", "archive", "proposals", "gates"]:
        (arc_dir / sub).mkdir(parents=True, exist_ok=True)

    for d in ["canon/manuscript", "canon/characters/character_mind_cards",
              "ledgers", "workspace", "workspace/reports"]:
        (root / d).mkdir(parents=True, exist_ok=True)

    for ledger_name, entries_key in [
        ("timeline", "events"),
        ("character_knowledge", "character_knowledge_entries"),
        ("foreshadowing", "foreshadowing_entries"),
    ]:
        lp = root / "ledgers" / f"{ledger_name}.json"
        if not lp.exists():
            lp.write_text(json.dumps({"schema_version": "1.0", entries_key: []}, indent=2))

    return arc_dir


def _read_keys_secure():
    """Return API config — caller must not log values."""
    return API_BASE, API_MODEL, "***" if API_KEY else ""


# ================================================================
# Crash Recovery — checkpoint after each chapter
# ================================================================

_CHECKPOINT_NAME = ".stress_checkpoint.json"


def _save_checkpoint(root: Path, data: dict):
    """Save checkpoint atomically (write tmp → rename)."""
    cp = root / _CHECKPOINT_NAME
    tmp = root / f"{_CHECKPOINT_NAME}.tmp"
    tmp.write_text(json.dumps(data, default=str), encoding="utf-8")
    tmp.replace(cp)


def _load_checkpoint(root: Path) -> dict | None:
    """Load checkpoint if it exists."""
    cp = root / _CHECKPOINT_NAME
    if cp.exists():
        try:
            return json.loads(cp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _clear_checkpoint(root: Path):
    """Remove checkpoint file after successful completion."""
    cp = root / _CHECKPOINT_NAME
    if cp.exists():
        cp.unlink(missing_ok=True)


def run_llm_stress_test(root: Path, num_chapters: int, resume: bool = False) -> dict:
    """Run full pipeline: LLM generate → apply → commit for N chapters.

    Tracks: tokens per chapter, context window growth, latency trends.
    Supports crash recovery: if resume=True and checkpoint exists, continues
    from last completed chapter.
    """
    results = {
        "num_chapters": num_chapters,
        "api_model": API_MODEL,
        "api_base_url_used": bool(API_BASE),
        "api_key_configured": bool(API_KEY),
        "chapters": [],
        "total_tokens_in": 0,
        "total_tokens_out": 0,
        "total_llm_latency_ms": 0,
        "total_apply_ms": 0,
        "apply_errors": 0,
        "llm_errors": 0,
    }

    if not API_KEY:
        results["error"] = "API key not configured"
        return results

    print(f"[INIT] LLM model: {API_MODEL}")
    print(f"[INIT] Target: {num_chapters} chapters with LLM generation")

    # Crash recovery: load checkpoint and resume
    start_ch = 1
    checkpoint_data = None
    if resume:
        checkpoint_data = _load_checkpoint(root)
        if checkpoint_data and checkpoint_data.get("completed_chapters"):
            start_ch = len(checkpoint_data["completed_chapters"]) + 1
            results["chapters"] = checkpoint_data["completed_chapters"]
            results["total_tokens_in"] = checkpoint_data.get("total_tokens_in", 0)
            results["total_tokens_out"] = checkpoint_data.get("total_tokens_out", 0)
            results["total_llm_latency_ms"] = checkpoint_data.get("total_llm_latency_ms", 0)
            history = checkpoint_data.get("history", [])
            print(f"[RESUME] Recovered from checkpoint: {len(checkpoint_data['completed_chapters'])} chapters done, resuming at ch_{start_ch:03d}")
            if start_ch > num_chapters:
                print("[RESUME] All chapters already completed!")
                results["passed"] = True
                results["commit_count"] = checkpoint_data.get("commit_count", 0)
                return results

    arc_dir = setup_stress_project(root, num_chapters)
    try:
        history
    except NameError:
        history: list[dict] = []  # Previous chapter summaries for context

    # Import kernel
    from novel_workflow.system_scripts.atomic_apply_manager import AtomicApplyManager
    from novel_workflow.schemas.gate import GateRecord
    from novel_workflow.schemas.diff import LedgerDiff
    from novel_workflow.schemas.chapter_commit import ChapterCommitStore
    from novel_workflow.system_scripts.projection_registry import ProjectionRegistry

    commit_store = ChapterCommitStore(root)
    registry = ProjectionRegistry(root)
    registry.register("index", registry.index_projection)
    registry.register("health", registry.health_projection)

    mgr = AtomicApplyManager(root)
    mgr.enable_chapter_commit(commit_store, registry)

    llm_start_ms = int(_time.time() * 1000)
    apply_start_ms = int(_time.time() * 1000)

    for i in range(start_ch, num_chapters + 1):
        ch_id = f"ch_{i:03d}"

        # --- LLM Generation ---
        prompt = build_context(i, history)
        prompt_tokens_est = _estimate_tokens(prompt)

        print(f"  [{ch_id}] Generating (context ~{prompt_tokens_est} tokens)...", end=" ", flush=True)
        llm = call_llm(prompt)

        if not llm.get("content") or llm.get("error"):
            results["llm_errors"] += 1
            err = llm.get("error", "empty response")
            print(f"ERROR: {err[:80]}")
            continue

        content = llm["content"]
        tokens_in = llm["tokens_in"]
        tokens_out = llm["tokens_out"]
        latency = llm["latency_ms"]

        print(f"{tokens_out}tok/{latency}ms")

        # Extract title
        title = f"Chapter {i}"
        lines = content.strip().split("\n")
        if lines and lines[0].startswith("#"):
            title = lines[0].lstrip("#").strip()

        # Write draft
        draft_path = arc_dir / "drafts" / f"{ch_id}.md"
        draft_path.write_text(content, encoding="utf-8")

        # Record in history for next chapter context
        history.append({
            "num": i,
            "title": title,
            "content": content,
            "summary": content[:400],
        })

        results["total_tokens_in"] += tokens_in
        results["total_tokens_out"] += tokens_out
        results["total_llm_latency_ms"] += latency

        # --- Apply Pipeline ---
        gate = GateRecord(
            gate_id=f"gate_stress_{ch_id}",
            gate_type="arc_end",
            target_artifact=f"arcs/stress_arc/drafts/{ch_id}.md",
            decision="approved",
            author_input_evidence=f"LLM stress test auto-approval — chapter {i}/{num_chapters} generated and verified",
            author_id="stress_test_runner",
            source_artifacts=[f"arcs/stress_arc/drafts/{ch_id}.md"],
        )

        diff = LedgerDiff(
            arc_id="stress_arc",
            operations=[{
                "target_ledger": "timeline",
                "operation": "append_event",
                "source_artifact": f"arcs/stress_arc/drafts/{ch_id}.md",
                "data": {
                    "event_id": f"evt_llm_{ch_id}",
                    "event_type": "chapter_written",
                    "chapter": ch_id,
                    "description": f"LLM-generated chapter {i}: {title}",
                },
            }],
        )

        try:
            result = mgr.apply(
                arc_id="stress_arc",
                gate_record=gate,
                draft_files=[f"{ch_id}.md"],
                ledger_diff=diff,
                canon_diff=None,
                dry_run=False,
            )
            results["chapters"].append({
                "chapter_id": ch_id,
                "num": i,
                "title": title,
                "status": "success",
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "total_tokens": tokens_in + tokens_out,
                "context_tokens": prompt_tokens_est,
                "llm_latency_ms": latency,
                "content_length": len(content),
                "finish_reason": llm.get("finish_reason", ""),
            })
            # Save checkpoint after each successful chapter for crash recovery
            _save_checkpoint(root, {
                "completed_chapters": results["chapters"],
                "total_tokens_in": results["total_tokens_in"],
                "total_tokens_out": results["total_tokens_out"],
                "total_llm_latency_ms": results["total_llm_latency_ms"],
                "history": history[-10:],  # Keep last 10 for context window
                "commit_count": commit_store.count,
                "last_chapter": i,
                "num_chapters": num_chapters,
            })
        except Exception as e:
            results["apply_errors"] += 1
            results["chapters"].append({
                "chapter_id": ch_id,
                "num": i,
                "status": "apply_failed",
                "error": str(e)[:200],
            })

        if i % 10 == 0:
            total_elapsed = int(_time.time() * 1000) - llm_start_ms
            avg_latency = results["total_llm_latency_ms"] // i if i > 0 else 0
            print(f"  ... {i}/{num_chapters} | avg latency: {avg_latency}ms | elapsed: {total_elapsed}ms")

    # Finalize
    results["total_apply_ms"] = int(_time.time() * 1000) - apply_start_ms
    total_elapsed = int(_time.time() * 1000) - llm_start_ms
    results["total_elapsed_ms"] = total_elapsed
    results["commit_count"] = commit_store.count

    # Derived stats
    completed = [c for c in results["chapters"] if c["status"] == "success"]
    if completed:
        results["avg_tokens_in"] = sum(c["tokens_in"] for c in completed) // len(completed)
        results["avg_tokens_out"] = sum(c["tokens_out"] for c in completed) // len(completed)
        results["avg_llm_latency_ms"] = sum(c["llm_latency_ms"] for c in completed) // len(completed)
        results["avg_content_length"] = sum(c["content_length"] for c in completed) // len(completed)
        results["context_growth"] = _analyze_context_growth(completed)

    # Allow up to 5% LLM transient errors (429/timeout) as long as 95% chapters committed
    total_error_rate = (results["apply_errors"] + results["llm_errors"]) / max(num_chapters, 1)
    results["passed"] = (
        results["apply_errors"] == 0
        and total_error_rate <= 0.05
        and results["commit_count"] >= num_chapters * 0.95
    )

    # Clear checkpoint on successful completion
    if results["passed"]:
        _clear_checkpoint(root)

    return results


def _estimate_tokens(text: str) -> int:
    """Rough token estimation: ~4 chars per token."""
    return len(text) // 4


def _analyze_context_growth(chapters: list[dict]) -> dict:
    """Analyze how context window grows across chapters."""
    if len(chapters) < 2:
        return {"trend": "insufficient_data"}

    first_ctx = chapters[0].get("context_tokens", 0)
    last_ctx = chapters[-1].get("context_tokens", 0)

    midpoints = []
    step = max(1, len(chapters) // 4)
    for i in range(0, len(chapters), step):
        midpoints.append({
            "chapter": chapters[i]["num"],
            "context_tokens": chapters[i].get("context_tokens", 0),
        })

    return {
        "first_context_tokens": first_ctx,
        "last_context_tokens": last_ctx,
        "growth": last_ctx - first_ctx,
        "growth_percent": round((last_ctx - first_ctx) / max(first_ctx, 1) * 100, 1),
        "growth_midpoints": midpoints,
    }


# ================================================================
# Main
# ================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="LLM-driven 100-chapter stress test")
    parser.add_argument("--chapters", type=int, default=20,
                        help="Number of chapters (default: 20)")
    parser.add_argument("--project-root", default="tools/stress_llm_output",
                        help="Output directory")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from last checkpoint after crash")
    args = parser.parse_args()

    root = Path(args.project_root)
    root.mkdir(parents=True, exist_ok=True)

    # Clean previous run (unless resuming)
    if not args.resume:
        for sub in ["arcs", "canon", "ledgers", "workspace"]:
            p = root / sub
            if p.exists():
                shutil.rmtree(p)

    if not API_KEY:
        print("[ERROR] No API key found. Place key.txt at C:/Users/18622/Desktop/key.txt")
        print("        Format: OPENAI_API_KEY=...  OPENAI_API_BASE=...  OPENAI_MODEL_NAME=...")
        return 1

    print("=" * 65)
    print(f"  Phase 3 LLM Stress Test — {args.chapters} chapters")
    print(f"  Model: {API_MODEL}")
    print("=" * 65)

    results = run_llm_stress_test(root, num_chapters=args.chapters, resume=args.resume)

    # Print summary (no API keys)
    print()
    print("=" * 65)
    print("  RESULTS")
    print("=" * 65)

    completed = sum(1 for c in results["chapters"] if c["status"] == "success")
    print(f"  Chapters: {completed}/{results['num_chapters']} generated & applied")
    print(f"  Apply errors: {results.get('apply_errors', 0)}")
    print(f"  LLM errors: {results.get('llm_errors', 0)}")
    print(f"  Commits: {results.get('commit_count', 0)}")

    if results.get("avg_tokens_in"):
        print()
        print(f"  Avg tokens IN:   {results['avg_tokens_in']}/ch")
        print(f"  Avg tokens OUT:  {results['avg_tokens_out']}/ch")
        print(f"  Total tokens IN:  {results['total_tokens_in']}")
        print(f"  Total tokens OUT: {results['total_tokens_out']}")
        print(f"  Avg LLM latency: {results['avg_llm_latency_ms']}ms/ch")
        print(f"  Total LLM time:  {results['total_llm_latency_ms']}ms")
        print(f"  Avg content len: {results['avg_content_length']} chars")

    cg = results.get("context_growth", {})
    if cg:
        print()
        print(f"  Context window: {cg.get('first_context_tokens', '?')} → {cg.get('last_context_tokens', '?')} tokens")
        print(f"  Context growth: {cg.get('growth_percent', '?')}%")

    print(f"\n  Total elapsed: {results.get('total_elapsed_ms', '?')}ms")
    passed = results.get("passed", False)
    print(f"\n  OVERALL: {'PASSED' if passed else 'FAILED'}")

    # Write detailed results
    result_path = root / "stress_results.json"
    safe_results = {k: v for k, v in results.items() if k not in ("api_key",)}
    result_path.write_text(json.dumps(safe_results, indent=2, default=str), encoding="utf-8")

    # Write per-chapter token report
    completed_count = sum(1 for c in results["chapters"] if c["status"] == "success")
    if completed_count > 0:
        token_report = root / "token_report.json"
        token_data = {
            "model": API_MODEL,
            "total_chapters": completed_count,
            "total_tokens_in": results.get("total_tokens_in", 0),
            "total_tokens_out": results.get("total_tokens_out", 0),
            "total_tokens": results.get("total_tokens_in", 0) + results.get("total_tokens_out", 0),
            "per_chapter": [
                {
                    "chapter": c["num"],
                    "tokens_in": c.get("tokens_in", 0),
                    "tokens_out": c.get("tokens_out", 0),
                    "context_tokens": c.get("context_tokens", 0),
                    "content_length": c.get("content_length", 0),
                    "latency_ms": c.get("llm_latency_ms", 0),
                }
                for c in results["chapters"]
                if c["status"] == "success"
            ],
        }
        token_report.write_text(json.dumps(token_data, indent=2), encoding="utf-8")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
