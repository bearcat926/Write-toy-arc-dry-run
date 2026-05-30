"""Test helpers for symlink creation with Windows fallback.

On Windows without admin privileges, os.symlink fails.
This helper falls back to mocking Path.is_symlink() so
symlink detection logic is still tested.
"""
import os
from pathlib import Path
from unittest.mock import patch


def try_symlink(src: str, dst: str) -> bool:
    """Try to create a symlink. Returns True if real symlink was created."""
    try:
        os.symlink(src, dst)
        return True
    except OSError:
        return False


class SymlinkFallback:
    """Context manager that creates a real symlink or mocks is_symlink().

    Usage:
        with SymlinkFallback(target_path, link_path) as sf:
            if sf.is_mock:
                # Real symlink not available, detection is mocked
                pass
            # Path.is_symlink() will return True for link_path
    """

    def __init__(self, target: str, link: str):
        self.target = target
        self.link = link
        self.is_mock = False
        self._patcher = None

    def __enter__(self):
        if try_symlink(self.target, self.link):
            self.is_mock = False
        else:
            # Fallback: mock is_symlink for the link path
            self.is_mock = True
            link_path = Path(self.link)
            original_is_symlink = Path.is_symlink

            def mock_is_symlink(self_path):
                if self_path == link_path or str(self_path) == str(link_path):
                    return True
                return original_is_symlink(self_path)

            self._patcher = patch.object(Path, 'is_symlink', mock_is_symlink)
            self._patcher.start()
            # Create the file/dir so path operations work
            if not os.path.exists(self.link):
                # Copy target to link location
                if os.path.isdir(self.target):
                    os.makedirs(self.link, exist_ok=True)
                else:
                    import shutil
                    shutil.copy2(self.target, self.link)
        return self

    def __exit__(self, *args):
        if self._patcher:
            self._patcher.stop()
        if not self.is_mock and os.path.islink(self.link):
            os.unlink(self.link)
