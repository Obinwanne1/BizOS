"""Load agent configuration from agents.yaml and settings.yaml."""
import yaml
from pathlib import Path
from functools import lru_cache

CONFIG_PATH = Path(__file__).parent.parent / "config" / "agents.yaml"
SETTINGS_PATH = Path(__file__).parent.parent / "config" / "settings.yaml"


@lru_cache(maxsize=1)
def load_agents_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_agent_cfg(agent_name: str) -> dict:
    config = load_agents_config()
    return config.get("agents", {}).get(agent_name, {})


def get_model(agent_name: str, fallback: str = "claude-sonnet-4-6") -> str:
    return get_agent_cfg(agent_name).get("model", fallback)


def get_max_tokens(agent_name: str, fallback: int = 4096) -> int:
    return get_agent_cfg(agent_name).get("max_tokens", fallback)


def get_persona(agent_name: str) -> str:
    return get_agent_cfg(agent_name).get("persona", "")


def get_orchestrator_model() -> str:
    config = load_agents_config()
    return config.get("orchestrator", {}).get("model", "claude-opus-4-8")


@lru_cache(maxsize=1)
def load_settings() -> dict:
    with open(SETTINGS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_limit(key: str, fallback: int = 20) -> int:
    return load_settings().get("limits", {}).get(key, fallback)
