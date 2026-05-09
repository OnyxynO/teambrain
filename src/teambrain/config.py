from __future__ import annotations
import json
from pathlib import Path

CONFIG_FILENAME = ".teambrain.json"
DEFAULT_CONFIG = {"model": "qwen3:1.7b"}


def find_decisions_dir() -> Path | None:
    """Remonte l'arborescence depuis le CWD pour trouver .decisions/."""
    for parent in [Path.cwd(), *Path.cwd().parents]:
        candidate = parent / ".decisions"
        if candidate.is_dir():
            return candidate
    return None


def load_config(decisions_dir: Path) -> dict:
    config_path = decisions_dir / CONFIG_FILENAME
    if config_path.exists():
        return {**DEFAULT_CONFIG, **json.loads(config_path.read_text())}
    return DEFAULT_CONFIG.copy()


def save_config(decisions_dir: Path, config: dict) -> None:
    config_path = decisions_dir / CONFIG_FILENAME
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False))
