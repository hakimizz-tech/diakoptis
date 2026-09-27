"""
Application settings and environment variable resolution (v2).
Follows 12-factor app principles by keeping config in the environment.
"""

import os
from dataclasses import dataclass, field
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
    templates_root: Path
    
    # Concurrency & Connections (v2)
    max_concurrent_sessions: int
    ssh_timeout: int
    
    # Logging & Debug
    log_level: str
    log_dir: Path
    netmiko_debug: bool

    command_path_dir: Path = field(init=False)
    command_map_paths: dict[str, Path] = field(init=False)


    def __post_init__(self):
        self.command_path_dir = Path(
            os.getenv("COMMAND_MAP_DIR", "config/command_map")
        )
        if not self.command_path_dir.is_dir():
            raise ValueError(
                f"Command map directory not found: {self.command_path_dir}"
            )

        self.command_map_paths = {
            path.stem.lower(): path
            for path in sorted(self.command_path_dir.iterdir())
            if path.is_file() and path.suffix.lower() in {".yaml", ".yml"}
        }

    def command_map_path_for(self, host_data: dict) -> Path:
        """Resolve one command-map file from inventory host metadata."""
        candidates = [
            str(host_data.get("device_type", "")).strip().lower(),
            str(host_data.get("vendor", "")).strip().lower(),
        ]
        for candidate in candidates:
            if candidate and candidate in self.command_map_paths:
                return self.command_map_paths[candidate]

        vendor = candidates[-1]
        vendor_maps = [
            path
            for name, path in self.command_map_paths.items()
            if vendor and name.startswith(f"{vendor}_")
        ]
        if len(vendor_maps) == 1:
            return vendor_maps[0]

        supported = ", ".join(sorted(self.command_map_paths)) or "none"
        raise ValueError(
            f"No command map found for host metadata {host_data!r}. "
            f"Available maps: {supported}"
        )



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
            os.getenv("INVENTORY_PATH", "config/inventory.yaml")
        ),

        templates_root=Path(
            os.getenv('TEMPLATES_ROOT_PATH', 'src/diakoptis/parsing/templates')
        ),
        
        # Concurrency controls for the SessionPool
        max_concurrent_sessions=int(
            os.getenv("MAX_CONCURRENT", "20")
        ),
        ssh_timeout=int(
            os.getenv("SSH_TIMEOUT", "15")
        ),
        
        # Logging & Debug
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        log_dir=Path(os.getenv("LOG_DIR", "logs/")),
        netmiko_debug=_parse_bool(os.getenv("NETMIKO_DEBUG", "False"))
    )


# Instantiate a global singleton for the app to use
SETTINGS = _load_settings()