"""
Vendor Driver Abstraction Base.
Defines the SwitchDriver interface that all specific vendor drivers must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any


class SwitchDriver(ABC):
    """
    Abstract Base Class for all network switch drivers.
    Enforces a standard contract (Liskov Substitution) so the core CLI 
    never needs to know the underlying vendor or connection library.
    """

    def __init__(self, hostname: str, host_data: Dict[str, Any], credentials: Dict[str, str]):
        """
        Initializes the driver with host configuration and resolved credentials.
        
        Args:
            hostname: The inventory name of the switch (e.g., 'lab-leaf01').
            host_data: Dictionary of host attributes (vendor, device_type, site, etc.).
            credentials: The resolved username, password, and optional secret.
        """
        self.hostname = hostname
        self.host_data = host_data
        self.credentials = credentials
        
        # Expose the vendor for the Command Resolver to look up the correct command map
        self.vendor = host_data.get("vendor", "unknown").lower()

    @abstractmethod
    def connect(self) -> None:
        """
        Establishes the connection to the switch.
        Must raise application-level exceptions (e.g., SwitchAuthError, SwitchTimeoutError)
        on failure, avoiding raw Netmiko or Paramiko stack traces leaking into the CLI.
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        Gracefully terminates the connection to the switch.
        Must be safe to call even if the connection is already closed.
        """
        pass

    @abstractmethod
    def send_native(self, commands: List[str]) -> Dict[str, str]:
        """
        Sends a list of native commands to the switch.
        
        Args:
            commands: List of raw strings to execute (e.g., ["show version", "show clock"]).
            
        Returns:
            A dictionary mapping the command string to its raw text output.
        """
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Returns True if the connection is currently active and usable.
        """
        pass