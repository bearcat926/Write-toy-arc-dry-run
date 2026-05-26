from pathlib import Path


def init_project(root: Path):
    dirs = [
        "canon/manuscript",
        "canon/characters/character_mind_cards",
        "ledgers",
        "gates",
        "workspace",
        "inspiration",
        "prompts",
        "variants",
        "profiles",
        "plugins",
    ]
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)
