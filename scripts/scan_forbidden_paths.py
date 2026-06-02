#!/usr/bin/env python3
"""Scan codebase for forbidden write paths bypassing the security kernel.

Rules:
  1. No agent code writes to canon/ or ledgers/
  2. Only AtomicApplyManager writes to ledgers/*.json
  3. Only Canonicalizer writes to canon/manuscript/
  4. No direct Path.write_text or open("w") to protected dirs
  5. No shutil.copy/copytree to protected dirs (except snapshot paths)

Usage:
    python scripts/scan_forbidden_paths.py [--project-root .] [--strict]

In strict mode, even test files are scanned (for CI safety).
In default mode, tests are excluded (they legitimately set up fixtures).

CI integration:
    Exits non-zero on violations.
"""

import ast
import os
import re
import sys
from pathlib import Path


# --- Protected directory patterns ---
FORBIDDEN_TARGETS = [
    "canon/manuscript",
    "canon/characters",
    "ledgers/",
    "ledgers",
]

# --- Modules allowed to write to protected dirs ---
ALLOWED_MODULES = {
    "atomic_apply_manager.py",
    "canonicalizer.py",
}

# --- Modules that reference protected paths for guard/policy definitions ---
GUARD_MODULES = {
    "path_safety.py",
    "derived_artifact_policy.py",
    "source_artifact_policy.py",
}

# --- Directories excluded from scan (relative path pattern) ---
EXCLUDE_DIRS = {
    "tests",
    "docs",
    "fixtures",
    "toy_project_llm",
    "toy_project_stress",
    "__pycache__",
    ".git",
    ".pytest_cache",
    ".venv",
    "venv",
    "node_modules",
    ".tox",
    "dist",
    "build",
    ".mypy_cache",
    ".workbuddy",
    "arcs",
}

# --- Root-level scripts allowed to touch ledgers for demo/setup ---
ROOT_SETUP_SCRIPTS = {
    "run_llm_dry_run.py",
    "run_long_arc_stress.py",
    "verify_llm_dry_run.py",
}

SNAPSHOT_PATTERN = re.compile(r"snapshot_|/archive/")
READ_PATTERN = re.compile(r"\.read|\.load|open\([^)]*['\"]['\"]r")
WRITE_PATTERN = re.compile(r"write_text\(|\.write\(|copy2\(|copytree\(|shutil\.copy|open\([^)]*['\"]['\"]w")


class Violation:
    def __init__(self, filepath: str, lineno: int, code: str, rule: str):
        self.filepath = filepath
        self.lineno = lineno
        self.code = code.strip()[:150]
        self.rule = rule

    def __str__(self):
        return f"  {self.filepath}:{self.lineno} [{self.rule}]\n    -> {self.code}"


def is_excluded(filepath: str) -> bool:
    """Check if file should be excluded from scan."""
    parts = filepath.replace("\\", "/").split("/")
    for part in parts:
        if part in EXCLUDE_DIRS:
            return True
    return False


def is_allowed(filepath: str) -> bool:
    """Check if file is allowed to reference protected paths."""
    filename = os.path.basename(filepath)

    if filename in ALLOWED_MODULES:
        return True
    if filename in GUARD_MODULES:
        return True
    if filename in ROOT_SETUP_SCRIPTS:
        return True

    return False


def scan_file(filepath: str, strict: bool = False) -> list[Violation]:
    """Scan a single file for violations."""
    violations: list[Violation] = []

    if not filepath.endswith(".py"):
        return violations
    if not strict and is_excluded(filepath):
        return violations
    if is_allowed(filepath):
        return violations

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        lines = source.split("\n")
    except (IOError, UnicodeDecodeError):
        return violations

    # --- Regex-based scan (covers all patterns) ---
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
            continue

        for pattern in FORBIDDEN_TARGETS:
            if pattern not in line:
                continue
            if SNAPSHOT_PATTERN.search(line):
                continue
            if READ_PATTERN.search(line) and not WRITE_PATTERN.search(line):
                continue

            # Check for write operations
            if WRITE_PATTERN.search(line):
                violations.append(Violation(
                    filepath, i, line,
                    f"Forbidden write to '{pattern}'"
                ))

    return violations


def scan_project(root: str, strict: bool = False) -> list[Violation]:
    """Scan entire project."""
    all_violations: list[Violation] = []

    for dirpath, dirnames, filenames in os.walk(root):
        # In strict mode, walk into everything; in default, skip excluded dirs
        if not strict:
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        else:
            # Still skip irrelevant dirs
            dirnames[:] = [d for d in dirnames if d not in {
                ".git", "__pycache__", ".pytest_cache", ".venv", "venv",
                "node_modules", ".tox", "dist", "build", ".mypy_cache", ".workbuddy",
            }]

        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            v = scan_file(filepath, strict=strict)
            all_violations.extend(v)

    return all_violations


def main():
    strict = "--strict" in sys.argv
    project_root = "."
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            project_root = arg
            break

    root = Path(project_root).resolve()

    mode = "STRICT" if strict else "DEFAULT (exclude tests/docs)"
    print(f"[SCAN] Mode: {mode}")
    print(f"[SCAN] Project: {root}")
    print()

    violations = scan_project(str(root), strict=strict)

    # Filter: only report src/ violations in non-strict mode, plus root scripts
    # (Tests are already excluded in non-strict)
    if not strict:
        src_violations = [v for v in violations
                          if "/src/" in v.filepath.replace("\\", "/")
                          or os.path.basename(v.filepath) in ROOT_SETUP_SCRIPTS]
    else:
        src_violations = violations

    if src_violations:
        print(f"[FAIL] {len(src_violations)} forbidden path violation(s):\n")
        for v in src_violations:
            print(str(v))
        print(f"\n[FAIL] Above code may bypass proposal/gate/apply security boundary.")
        print("[FAIL] If legitimate, add file to ALLOWED_MODULES or GUARD_MODULES in this script.")
        sys.exit(1)
    else:
        print("[PASS] No forbidden path violations in source code")
        sys.exit(0)


if __name__ == "__main__":
    main()
