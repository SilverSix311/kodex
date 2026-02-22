"""Agent Info management — stores agent-specific information.

Data is stored in agent_info.json and exposed as global variables:
  %agent_name%, %agent_email%, %agent_team%, %agent_workdays%, 
  %agent_shift%, %agent_company%
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class AgentInfo:
    """Agent information data structure."""
    name: str = ""
    email: str = ""
    team: str = ""
    workdays: str = ""  # e.g., "Sunday, Monday, Tuesday, Wednesday, Thursday"
    shift: str = ""     # e.g., "9am-6pm"
    company: str = ""
    
    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "AgentInfo":
        """Create from dictionary."""
        return cls(
            name=data.get("name", ""),
            email=data.get("email", ""),
            team=data.get("team", ""),
            workdays=data.get("workdays", ""),
            shift=data.get("shift", ""),
            company=data.get("company", ""),
        )


def _get_data_dir() -> Path:
    """Get the Kodex data directory."""
    kodex_root = os.environ.get("KODEX_ROOT")
    if kodex_root:
        portable_data = Path(kodex_root) / "data"
        home_data = Path.home() / ".kodex"
        if portable_data.exists() or not home_data.exists():
            return portable_data
    return Path.home() / ".kodex"


def get_agent_info_path(data_dir: Path | None = None) -> Path:
    """Get path to agent_info.json."""
    data_dir = data_dir or _get_data_dir()
    return data_dir / "agent_info.json"


def load_agent_info(data_dir: Path | None = None) -> AgentInfo:
    """Load agent info from JSON file."""
    path = get_agent_info_path(data_dir)
    
    if not path.exists():
        return AgentInfo()
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return AgentInfo.from_dict(data)
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Failed to load agent_info.json: %s", e)
        return AgentInfo()


def save_agent_info(info: AgentInfo, data_dir: Path | None = None) -> None:
    """Save agent info to JSON file."""
    path = get_agent_info_path(data_dir)
    
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(info.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
        log.info("Saved agent info to %s", path)
    except OSError as e:
        log.error("Failed to save agent_info.json: %s", e)
        raise


def get_agent_variable(name: str, data_dir: Path | None = None) -> str | None:
    """Get a specific agent variable by name.
    
    Supported names: agent_name, agent_email, agent_team, 
                     agent_workdays, agent_shift, agent_company
    """
    info = load_agent_info(data_dir)
    
    mapping = {
        "agent_name": info.name,
        "agent_email": info.email,
        "agent_team": info.team,
        "agent_workdays": info.workdays,
        "agent_shift": info.shift,
        "agent_company": info.company,
    }
    
    return mapping.get(name)
