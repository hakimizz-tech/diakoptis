"""
Session Pool Manager.
Manages multiple concurrent connections to SwitchDriver instances.
Uses ThreadPoolExecutor to fan-out commands to all active sessions in parallel.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional

from diakoptis.drivers.base import SwitchDriver
from diakoptis.drivers.factory import get_driver, UnsupportedVendorError
from diakoptis.connection.exceptions import SwitchConnectionError


class SessionPool:
    """
    Manages a pool of active network switch sessions.
    Responsible for parallel execution of commands across all targeted hosts.
    """

    def __init__(self, max_workers: int = 20):
        """
        Initializes the pool.
        
        Args:
            max_workers: The maximum number of concurrent threads to spawn.
                         Netmiko is purely I/O bound, so higher numbers (20-50) are safe.
        """
        self.max_workers = max_workers
        
        # Maps hostname -> active SwitchDriver instance
        self.active_sessions: Dict[str, SwitchDriver] = {}

    def connect_all(
        self, 
        targets: List[str], 
        inventory, 
        credentials_mgr
    ) -> Dict[str, Optional[str]]:
        """
        Spawns a thread pool to connect to all specified targets simultaneously.
        
        Returns:
            A dictionary mapping hostname -> error message (if failed) or None (if successful).
        """
        results = {}
        
        def _connect_worker(hostname: str):
            """Internal worker function executed by the thread pool."""
            try:
                host_data = inventory.get_host(hostname)
                
                # 1. Resolve Credentials for this specific host
                profile_name = host_data.get("credential_profile", "default")
                creds = credentials_mgr.resolve(profile_name)
                
                # 2. Instantiate the correct Driver via Factory
                driver = get_driver(hostname, host_data, creds)
                
                # 3. Open the SSH connection
                driver.connect()
                
                return hostname, driver, None
                
            except Exception as e:
                return hostname, None, str(e)

        # Execute connection attempts in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(_connect_worker, host) for host in targets]
            
            for future in as_completed(futures):
                hostname, driver, error = future.result()
                
                if error:
                    results[hostname] = error
                else:
                    if driver is None:
                        results[hostname] = "Driver creation failed without an error message."
                        continue
                    self.active_sessions[hostname] = driver
                    results[hostname] = None

        return results

    def send_commands_all(self, commands: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Fans out a list of native commands to all active sessions in parallel.
        
        Args:
            commands: List of native CLI strings (e.g., ["show version", "show clock"]).
            
        Returns:
            A nested dictionary: { "switch1": { "show clock": "14:00...", "show version": "..." }, ... }
        """
        if not self.active_sessions:
            raise SwitchConnectionError("Cannot send commands: No active sessions in the pool.")

        results = {}
        
        def _command_worker(driver: SwitchDriver):
            """Internal worker to execute commands on a single driver."""
            try:
                # The driver returns { "cmd": "raw output" }
                return driver.hostname, driver.send_native(commands)
            except Exception as e:
                # If the driver crashes completely, wrap the error in the expected format
                error_dict = {cmd: f"Driver execution error: {str(e)}" for cmd in commands}
                return driver.hostname, error_dict

        # Execute commands in parallel across all active connections
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(_command_worker, driver) for driver in self.active_sessions.values()]
            
            for future in as_completed(futures):
                hostname, output_data = future.result()
                results[hostname] = output_data
                
        return results

    def disconnect_all(self) -> None:
        """
        Gracefully disconnects all active sessions and clears the pool.
        """
        def _disconnect_worker(driver: SwitchDriver):
            driver.disconnect()
            
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # We don't care about the results/exceptions of disconnect, 
            # we just fire them off concurrently to tear down quickly.
            for driver in self.active_sessions.values():
                executor.submit(_disconnect_worker, driver)
                
        self.active_sessions.clear()

    @property
    def has_active_sessions(self) -> bool:
        """Returns True if there is at least one active connection in the pool."""
        return len(self.active_sessions) > 0
    
    @property
    def active_hostnames(self) -> List[str]:
        """Returns a sorted list of currently connected hostnames."""
        return sorted(list(self.active_sessions.keys()))