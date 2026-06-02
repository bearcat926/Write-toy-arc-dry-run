import os
from pathlib import Path


def _load_key_file() -> dict[str, str]:
    """Load API keys from key.txt when env vars are not set. Never logged."""
    env = {}
    for kp in [Path("C:/Users/18622/Desktop/key.txt")]:
        try:
            for line in kp.read_text(encoding="utf-8").strip().split("\n"):
                if "=" in line and not line.strip().startswith("#"):
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip()
        except (FileNotFoundError, PermissionError):
            pass
    return env


_key_env = _load_key_file()

LLM_MODEL = os.environ.get("OPENAI_MODEL_NAME", _key_env.get("OPENAI_MODEL_NAME", ""))
LLM_BASE_URL = os.environ.get("OPENAI_API_BASE", _key_env.get("OPENAI_API_BASE", ""))
LLM_API_KEY = os.environ.get("OPENAI_API_KEY", _key_env.get("OPENAI_API_KEY", ""))
