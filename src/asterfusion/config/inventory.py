"""
Inventory configuration loader.
Parses inventory.yaml, flattens host inheritance, and resolves environment variables.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional

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
        self.hosts: Dict[str, Dict[str, Any]] = {}
        
        self._load_and_flatten()

    def _resolve_env_vars(self, value: Any) -> Any:
        """
        Checks if a string value is an environment variable reference (starts with 'ENV:').
        If so, fetches it from os.environ. Otherwise, returns the value as-is.
        """
        if isinstance(value, str) and value.startswith("ENV:"):
            env_key = value.split("ENV:", 1)[1].strip()
            # Return the env var, or an empty string if it's not set
            return os.getenv(env_key, "")
        return value

    def _load_and_flatten(self) -> None:
        """
        Loads the YAML file and flattens the defaults -> groups -> hosts hierarchy
        into a single flat dictionary of hosts.
        """
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

        defaults = data.get("defaults", {})
        groups = data.get("groups", {})

        # Iterate through groups and flatten the inheritance tree
        for group_name, group_data in groups.items():
            if not group_data:
                continue
                
            # Extract group-level variables (everything except the 'hosts' dictionary)
            group_vars = {k: v for k, v in group_data.items() if k != "hosts"}
            group_hosts = group_data.get("hosts", {})

            for host_name, host_data in group_hosts.items():
                if not host_data:
                    host_data = {}

                # Merge dictionaries. Order of precedence (lowest to highest):
                # 1. Global defaults
                # 2. Group overrides
                # 3. Host-specific overrides
                merged_host = {**defaults, **group_vars, **host_data}
                
                # Resolve any ENV: variable references securely
                resolved_host = {
                    k: self._resolve_env_vars(v) 
                    for k, v in merged_host.items()
                }
                
                self.hosts[host_name] = resolved_host

    def get_host(self, target_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the fully resolved connection dictionary for a specific host.
        
        Args:
            target_name: The name of the host (e.g., 'lab-leaf01').
            
        Returns:
            A dictionary of connection parameters, or None if the host isn't found.
        """
        return self.hosts.get(target_name)

    def list_hosts(self) -> list[str]:
        """Returns a list of all configured hostnames."""
        return list(self.hosts.keys())