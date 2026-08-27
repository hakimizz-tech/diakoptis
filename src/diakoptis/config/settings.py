"""
Application settings and environment variable resolution (v2).
Follows 12-factor app principles by keeping config in the environment.
"""

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
    # Auto-loads variables from a local .env file if it exists.
    # Crucial for local dev to source credentials and paths safely.
    load_dotenv()  
except ImportError:
    pass  # In production, we assume variables are injected by the OS/Container

@dataclass
class Settings:
    """Strongly-typed application settings."""
    # File Paths
    inventory_path: Path
    command_map_path: Path
    templates_root: Path
    
    # Concurrency & Connections (v2)
    max_concurrent_sessions: int
    ssh_timeout: int
    
    # Logging & Debug
    log_level: str
    log_dir: Path
    netmiko_debug: bool


def _parse_bool(value: str) -> bool:
    """Helper to convert environment variable strings to booleans."""
    return str(value).strip().lower() in ("true", "1", "yes", "t", "y")


def _load_settings() -> Settings:
    """
    Reads environment variables and constructs the Settings object.
    Provides sane default values if environment variables are not set.
    """
    return Settings(
        # File paths updated to match the v2 folder structure
        inventory_path=Path(
            os.getenv("ASTER_CLI_INVENTORY_PATH", "config/inventory.yaml")
        ),
        command_map_path=Path(
            os.getenv("ASTER_CLI_COMMAND_MAP_PATH", "config/command_map/asterfusion.yaml")
        ),

        templates_root=Path(
            os.getenv('TEMPLATES_ROOT_PATH', 'src/asterfusion/parsing/templates/')
        ),
        
        # Concurrency controls for the SessionPool
        max_concurrent_sessions=int(
            os.getenv("ASTER_CLI_MAX_CONCURRENT", "20")
        ),
        ssh_timeout=int(
            os.getenv("ASTER_CLI_SSH_TIMEOUT", "15")
        ),
        
        # Logging & Debug
        log_level=os.getenv("ASTER_CLI_LOG_LEVEL", "INFO").upper(),
        log_dir=Path(os.getenv("ASTER_CLI_LOG_DIR", "logs/")),
        netmiko_debug=_parse_bool(os.getenv("ASTER_CLI_NETMIKO_DEBUG", "False"))
    )


# Instantiate a global singleton for the app to use
SETTINGS = _load_settings()