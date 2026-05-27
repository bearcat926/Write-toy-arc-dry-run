import shutil
from pathlib import Path
from ..guards.path_safety import PathSafetyGuard


class Canonicalizer:
    def __init__(self, project_root: Path):
        self._root = project_root
        self._guard = PathSafetyGuard(project_root)

    def canonicalize(self, arc_id: str, draft_files: list[str]):
        dest = self._root / "canon" / "manuscript"
        dest.mkdir(parents=True, exist_ok=True)
        src_dir = self._root / "arcs" / arc_id / "drafts"
        for f in draft_files:
            src = src_dir / f
            if src.exists():
                self._guard.check_write_path(f"canon/manuscript/{f}", "system_script", artifact_type="canon_manuscript_copy")
                shutil.copy2(src, dest / f)
