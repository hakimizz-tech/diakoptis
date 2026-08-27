"""
Credential Profile Resolver.
Resolves named credential profiles from the inventory into actual 
passwords via environment variables, ensuring no secrets are stored in plaintext.
"""

import os
from typing import Dict, Any


class CredentialResolutionError(Exception):
    """Raised when a credential profile cannot be fully resolved to valid secrets."""
    pass


class CredentialManager:
    """
    Manages the resolution of credential profiles.
    Reads the 'credential_profiles' block from the inventory object.
    """

    def __init__(self, inventory):
        """
        Initializes the manager.
        
        Args:
            inventory: The loaded Inventory object, which must have a get_profiles() method.
        """
        self.inventory = inventory

    def resolve(self, profile_name: str) -> Dict[str, str]:
        """
        Resolves a named profile into a dictionary of actual credentials.
        
        Args:
            profile_name: The name of the profile (e.g., 'default', 'leaf_admin').
            
        Returns:
            A dictionary containing 'username', 'password', and optionally 'secret'.
            
        Raises:
            CredentialResolutionError: If the profile is undefined or env vars are missing.
        """
        if not profile_name:
            profile_name = "default"

        # 1. Fetch the profile definition from the inventory
        profiles = self.inventory.get_profiles()
        profile_def = profiles.get(profile_name)

        if not profile_def:
            raise CredentialResolutionError(
                f"Credential profile '{profile_name}' is referenced by a host, "
                f"but is not defined in the 'credential_profiles' section of inventory.yaml."
            )

        # 2. Extract the environment variable keys
        user_env_key = profile_def.get("username_env")
        pass_env_key = profile_def.get("password_env")
        secret_env_key = profile_def.get("secret_env") # Optional (enable password)

        if not user_env_key or not pass_env_key:
            raise CredentialResolutionError(
                f"Credential profile '{profile_name}' is invalid. "
                "It must define both 'username_env' and 'password_env'."
            )

        # 3. Resolve the actual values from the OS environment
        resolved_creds = {}
        
        username = os.environ.get(user_env_key)
        password = os.environ.get(pass_env_key)
        
        if not username or not password:
            raise CredentialResolutionError(
                f"Failed to resolve profile '{profile_name}'. "
                f"Environment variables {user_env_key} and/or {pass_env_key} are missing or empty. "
                "Did you forget to source your .env file?"
            )
            
        resolved_creds["username"] = username
        resolved_creds["password"] = password

        # 4. Resolve the optional enable secret
        if secret_env_key:
            secret = os.environ.get(secret_env_key)
            if secret:
                resolved_creds["secret"] = secret
            else:
                # We don't fail hard here, as some setups use the main password for enable
                resolved_creds["secret"] = password

        return resolved_creds