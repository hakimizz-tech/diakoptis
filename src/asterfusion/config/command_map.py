"""
Command Map configuration loader.
Parses, validates, and stores the friendly-to-native command mappings.
"""

import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


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


class CommandMap:
    def __init__(self, filepath: str = "config/command_map.yaml"):
        """
        Initializes the command map by loading and parsing the YAML file.
        
        Args:
            filepath: Path to the command_map.yaml file.
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
                "Ensure config/command_map.yaml exists."
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
            
            # Ensure 'native' is always a list, even if the user only put one command as a string
            native_cmds = cmd_data["native"]
            if isinstance(native_cmds, str):
                native_cmds = [native_cmds]

            # Construct the dataclass
            self.commands[cmd_key] = CommandDefinition(
                description=cmd_data.get("description", "No description provided."),
                native=native_cmds,
                parse=cmd_data["parse"]
            )

    def get_command(self, command_key: str) -> Optional[CommandDefinition]:
        """
        Retrieves a validated command definition by its key (e.g., 'show_interfaces').
        
        Args:
            command_key: The friendly command name.
            
        Returns:
            A CommandDefinition object, or None if the command isn't mapped.
        """
        return self.commands.get(command_key)

    def list_commands(self) -> List[str]:
        """Returns a list of all available friendly command keys."""
        return list(self.commands.keys())