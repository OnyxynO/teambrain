from __future__ import annotations
import json
from pathlib import Path

CONFIG_FILENAME = ".teambrain.json"
DEFAULT_CONFIG = {
    "model": "qwen3:1.7b",
    "embedding_model": "qwen3-embedding:0.6b",
    "module_mappings": {},
    "chat": {
        "platform": "slack",
        "channels": [],
        "bot_token_env": "SLACK_BOT_TOKEN",
        "app_token_env": "SLACK_APP_TOKEN",
        "lead_user_id_env": "TEAMBRAIN_LEAD",
        "confidence_threshold": 0.7,
    },
    "github": {
        "token_env": "GITHUB_TOKEN",
        "repo_env": "GITHUB_REPO",
    },
}


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
