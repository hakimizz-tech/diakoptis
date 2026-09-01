"""
Command Map configuration loader (v2).
Parses, validates, and stores the friendly-to-native command mappings.
"""

import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union


class CommandMapError(Exception):
    """Custom exception for command map loading and validation errors."""
    pass


@dataclass
class CommandDefinition:
    """
    Represents a single command mapping loaded from the YAML file.
    """
    description: str
    native: List[str]
    parse: str
    ntc_override: Optional[Dict[str, str]] = None


class CommandMap:
    def __init__(self, filepath: Union[str, Path] = "config/command_map/asterfusion.yaml"):
        """
        Initializes the command map by loading and parsing the YAML file.
        
        Args:
            filepath: Path to the vendor-specific command map YAML file.
        """
        self.filepath = Path(filepath)
        self.commands: Dict[str, CommandDefinition] = {}
        
        self._load_and_validate()

    def _load_and_validate(self) -> None:
        """
        Loads the YAML file and validates that every command has the required fields.
        """
        if not self.filepath.exists():
            raise CommandMapError(
                f"Command map file not found at {self.filepath}. "
                "Ensure your config/command_map/ directory contains the correct vendor YAML."
            )

        try:
            with open(self.filepath, "r") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise CommandMapError(f"Failed to parse YAML in {self.filepath}: {e}")

        for cmd_key, cmd_data in data.items():
            # Validate required fields
            if "native" not in cmd_data:
                raise CommandMapError(f"Command '{cmd_key}' is missing the required 'native' key.")
            if "parse" not in cmd_data:
                raise CommandMapError(f"Command '{cmd_key}' is missing the required 'parse' key.")
            if 'description' not in cmd_data:
                raise CommandMapError(f"command '{cmd_key}' is missing the required 'description' key ")
            
            # Ensure 'native' is always a list, even if the user only put one command as a string
            native_cmds = cmd_data["native"]
            if isinstance(native_cmds, str):
                native_cmds = [native_cmds]

            ntc_override = cmd_data.get("ntc_override")
            if ntc_override is not None:
                if not isinstance(ntc_override, dict):
                    raise CommandMapError(
                        f"Command '{cmd_key}' has an invalid 'ntc_override' value; it must be a mapping with 'platform' and 'command'."
                    )
                missing_keys = [key for key in ("platform", "command") if key not in ntc_override]
                if missing_keys:
                    raise CommandMapError(
                        f"Command '{cmd_key}' is missing required ntc_override keys: {', '.join(missing_keys)}."
                    )
                if not all(isinstance(ntc_override[key], str) for key in ("platform", "command")):
                    raise CommandMapError(
                        f"Command '{cmd_key}' has a malformed 'ntc_override'; 'platform' and 'command' must both be strings."
                    )

            # Construct the dataclass. 
            # Note: Parameterized targets like {target} remain as raw strings here.
            # The CommandResolver handles injecting the actual target values later.
            self.commands[cmd_key] = CommandDefinition(
                description=cmd_data.get("description"),
                native=native_cmds,
                parse=cmd_data["parse"],
                ntc_override=ntc_override,
            )

    def get_command(self, command_key: str) -> Optional[CommandDefinition]:
        """
        Retrieves a validated command definition by its key (e.g., 'check_interfaces').
        
        Args:
            command_key: The friendly command name.
            
        Returns:
            A CommandDefinition object, or None if the command isn't mapped.
        """
        return self.commands.get(command_key)

    def list_commands(self) -> List[str]:
        """Returns a list of all available friendly command keys."""
        return list(self.commands.keys())