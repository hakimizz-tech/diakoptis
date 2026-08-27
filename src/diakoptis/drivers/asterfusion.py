"""
Asterfusion AsterNOS Driver.
Implements the SwitchDriver interface using Netmiko.
"""

from typing import Any, Dict, List, Optional
import logging
from asterfusion.drivers.base import SwitchDriver
from asterfusion.connection.exceptions import (
    SwitchAuthError,
    SwitchTimeoutError,
    SwitchConnectionError
)

# Netmiko is only imported here, inside the specific vendor driver.
from netmiko import ConnectHandler, NetmikoAuthenticationException, NetmikoTimeoutException


class AsterfusionDriver(SwitchDriver):
    """
    Driver for Asterfusion switches running AsterNOS (SONiC).
    Uses Netmiko under the hood with the 'asterfusion_asternos' device_type.
    """

    def __init__(self, hostname: str, host_data: Dict[str, Any], credentials: Dict[str, str]):
        super().__init__(hostname, host_data, credentials)
        
        self.ip_address = self.host_data.get("host")
        if not self.ip_address:
            raise ValueError(f"Host '{self.hostname}' is missing an IP address ('host' field) in inventory.")

        # Ensure we always use the correct device type for this driver
        self.device_type = self.host_data.get("device_type", "asterfusion_asternos")
        
        self.netmiko_conn: Optional[Any] = None
        
        # Suppress noisy Netmiko/Paramiko background logs unless explicitly needed
        logging.getLogger("netmiko").setLevel(logging.CRITICAL)
        logging.getLogger("paramiko").setLevel(logging.CRITICAL)

    def connect(self) -> None:
        """
        Establishes the Netmiko SSH session.
        """
        connection_params = {
            "device_type": self.device_type,
            "host": self.ip_address,
            "username": self.credentials.get("username"),
            "password": self.credentials.get("password"),
            "global_delay_factor": 2, # SONiC can occasionally be slow to return the prompt
            "timeout": 15,
        }
        
        # Add the enable secret if provided
        secret = self.credentials.get("secret")
        if secret:
            connection_params["secret"] = secret

        try:
            self.netmiko_conn = ConnectHandler(auto_connect=False, **connection_params)
            self.netmiko_conn._open()
            
            # Optional: If your AsterNOS switches drop you into bash instead of the CLI, 
            # you would handle that transition here (e.g., self.netmiko_conn.send_command("sonic-cli")).
            
            # Ensure we are in enable mode if a secret was provided
            if secret and not self.netmiko_conn.check_enable_mode():
                self.netmiko_conn.enable()

        except NetmikoAuthenticationException as e:
            username = self.credentials.get("username", "unknown user")
            raise SwitchAuthError(f"Authentication failed for {username} on {self.hostname}.") from e
        
        except NetmikoTimeoutException as e:
            raise SwitchTimeoutError(f"Connection to {self.hostname} ({self.ip_address}) timed out.") from e
        
        except Exception as e:
            raise SwitchConnectionError(f"Failed to connect to {self.hostname}: {e}") from e

    def disconnect(self) -> None:
        """
        Gracefully terminates the connection.
        """
        if self.is_connected:
            connection = self.netmiko_conn
            if connection is None:
                return
            try:
                connection.disconnect()
            except Exception:
                pass # Fail silently on disconnect, the socket is likely already dead
        self.netmiko_conn = None

    def send_native(self, commands: List[str]) -> Dict[str, str]:
        """
        Executes a list of native commands.
        Uses use_textfsm=False to ensure we always get raw text back.
        """
        if not self.is_connected:
            raise SwitchConnectionError(f"Cannot send commands: Not connected to {self.hostname}.")

        connection = self.netmiko_conn
        if connection is None:
            raise SwitchConnectionError(f"Cannot send commands: Not connected to {self.hostname}.")

        results = {}
        for cmd in commands:
            try:
                # We handle TextFSM parsing in our own OutputParser layer, 
                # so we explicitly tell Netmiko to return raw text.
                output = connection.send_command(cmd, use_textfsm=False)
                results[cmd] = output
                
            except Exception as e:
                # If a single command fails, record the error in the output dictionary 
                # instead of crashing the whole batch.
                results[cmd] = f"Error executing command: {str(e)}"

        return results

    @property
    def is_connected(self) -> bool:
        """Checks if the Netmiko socket is active."""
        if not self.netmiko_conn:
            return False
        return self.netmiko_conn.is_alive()