"""
Connection Manager module.
Wraps netmiko.ConnectHandler to manage SSH sessions and execute commands.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoTimeoutException,
    NetmikoAuthenticationException,
    ConnectionException
)

# Import the custom exceptions we just created
from asterfusion.connection.exceptions import (
    SwitchConnectionError,
    SwitchAuthError,
    SwitchTimeoutError
)
from asterfusion.config.settings import SETTINGS



class ConnectionManager:
    def __init__(self):
        """Initializes the manager with no active connection."""
        self.connection = None
        self.active_host_name: Optional[str] = None
        
        # Configure global Netmiko debug logging if enabled in .env
        if SETTINGS.netmiko_debug:
            logging.basicConfig(level=logging.DEBUG)
            logging.getLogger("netmiko").setLevel(logging.DEBUG)

    def connect(self, host_name: str, host_data: Dict[str, Any]) -> None:
        """
        Establishes an SSH connection to the target switch.
        
        Args:
            host_name: The friendly name of the host (e.g., 'lab-leaf01').
            host_data: The dictionary of connection parameters resolved by the Inventory.
            
        Raises:
            SwitchAuthError: On invalid credentials.
            SwitchTimeoutError: On unreachability.
            SwitchConnectionError: On other socket/SSH errors.
        """
        # Ensure any existing connection is closed first
        self.disconnect()

        # Prepare the Netmiko session log path (e.g., logs/lab-leaf01_20260821.log)
        timestamp = datetime.now().strftime("%Y%m%d")
        log_filename = SETTINGS.log_dir / f"{host_name}_{timestamp}.log"
        
        # Ensure the log directory exists
        SETTINGS.log_dir.mkdir(parents=True, exist_ok=True)

        # Build the Netmiko connection dictionary
        netmiko_kwargs = {
            "device_type": host_data.get("device_type", "asterfusion_asternos"),
            "host": host_data.get("hostname"),
            "username": host_data.get("username"),
            "password": host_data.get("password"),
            "secret": host_data.get("secret", ""),
            "port": host_data.get("port", 22),
            "session_log": str(log_filename),
            # Prevents hanging if the switch prompt is unusual
            "global_delay_factor": 1, 
        }

        try:
            self.connection = ConnectHandler(auto_connect=False, **netmiko_kwargs)
            self.connection._open()
            
            # If a privilege EXEC password (enable) was provided, elevate privileges
            if netmiko_kwargs["secret"]:
                self.connection.enable()
                
            self.active_host_name = host_name
            
        except NetmikoAuthenticationException as e:
            raise SwitchAuthError(f"Authentication failed for {host_name}. Check credentials.") from e
        except NetmikoTimeoutException as e:
            raise SwitchTimeoutError(f"Connection to {host_name} timed out. Is it reachable?") from e
        except Exception as e:
            raise SwitchConnectionError(f"Failed to connect to {host_name}: {str(e)}") from e

    def disconnect(self) -> None:
        """Gracefully closes the active SSH connection."""
        if self.connection:
            try:
                self.connection.disconnect()
            except Exception:
                pass
            finally:
                self.connection = None
                self.active_host_name = None

    def send_commands(self, commands: List[str]) -> Dict[str, str]:
        """
        Sends a list of native commands to the connected switch.
        
        Args:
            commands: A list of native command strings (e.g., ["show interface status"]).
            
        Returns:
            A dictionary mapping the command string to its raw text output.
            
        Raises:
            SwitchConnectionError: If no switch is currently connected.
        """
        if not self.connection:
            raise SwitchConnectionError("Cannot send commands: No active connection.")

        results = {}
        for cmd in commands:
            try:
                # send_command handles sending the string, waiting for the prompt, 
                # and returning the raw string output.
                output = self.connection.send_command(cmd)
                results[cmd] = output
            except Exception as e:
                # We capture the error in the results so the CLI doesn't crash 
                # if just one command in a multi-command playbook fails.
                results[cmd] = f"ERROR executing command: {str(e)}"
                
        return results

    @property
    def is_connected(self) -> bool:
        """Returns True if a session is currently active."""
        return self.connection is not None