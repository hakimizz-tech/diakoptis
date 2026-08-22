"""
Inventory configuration loader (v2).
Parses inventory.yaml and provides data access methods for the 
TargetParser, SessionPool, and CredentialManager.
"""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional


class InventoryError(Exception):
    """Custom exception for inventory loading errors."""
    pass


class Inventory:
    def __init__(self, filepath: str = "config/inventory.yaml"):
        """
        Initializes the inventory by loading and parsing the YAML file.
        
        Args:
            filepath: Path to the inventory.yaml file.
        """
        self.filepath = Path(filepath)
        
        # Internal data stores mapping to the v2 YAML schema
        self._switches: Dict[str, Dict[str, Any]] = {}
        self._groups: Dict[str, List[str]] = {}
        self._profiles: Dict[str, Dict[str, str]] = {}
        
        self._load_config()

    def _load_config(self) -> None:
        """Loads the flat YAML file into memory."""
        if not self.filepath.exists():
            raise InventoryError(
                f"Inventory file not found at {self.filepath}. "
                "Did you copy config/inventory.yaml.example to config/inventory.yaml?"
            )

        try:
            with open(self.filepath, "r") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise InventoryError(f"Failed to parse YAML in {self.filepath}: {e}")

        # The v2 schema uses 'switches' instead of 'hosts'
        self._switches = data.get("switches", {})
        self._groups = data.get("groups", {})
        self._profiles = data.get("credential_profiles", {})

        if not self._switches:
            raise InventoryError(f"No 'switches' defined in {self.filepath}.")

    # Data Access Methods used by the CLI components

    def get_host(self, target_name: str) -> Dict[str, Any]:
        """
        Retrieves the configuration dictionary for a specific switch.
        
        Args:
            target_name: The name of the switch (e.g., 'switch1').
            
        Returns:
            A dictionary of host attributes.
            
        Raises:
            InventoryError: If the switch is not found.
        """
        if target_name not in self._switches:
            raise InventoryError(f"Switch '{target_name}' not found in inventory.")
        return self._switches[target_name]

    def list_hosts(self) -> List[str]:
        """Returns a list of all configured switch names."""
        return list(self._switches.keys())

    def get_group(self, group_name: str) -> Optional[List[str]]:
        """
        Retrieves the list of switch names belonging to a curated group.
        Used by the TargetParser to resolve queries like '@core_uplinks'.
        """
        return self._groups.get(group_name)

    def get_profiles(self) -> Dict[str, Dict[str, str]]:
        """
        Retrieves the dictionary of credential profiles.
        Used by the CredentialManager to resolve secure environment variables.
        """
        return self._profiles