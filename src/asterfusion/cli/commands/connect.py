"""
Connect command handler.
Handles initiating an SSH session to a target switch via the Connection Manager.
"""

from asterfusion.logging.session_log import audit_logger
from asterfusion.connection.exceptions import (
    SwitchAuthError,
    SwitchTimeoutError,
    SwitchConnectionError
)


def execute(args: list[str], shell_instance) -> None:
    """
    Executes the 'connect' command.
    
    Args:
        args: List of string arguments provided by the user (e.g., ['lab-leaf01']).
        shell_instance: The AsterfusionCLI instance (to update state and access managers).
    """
    if not args:
        print("[!] Usage: connect <host>")
        print("    Hint: <host> must match a name defined in your inventory.yaml")
        return

    target = args[0]
    
    # 1. Inventory Lookup
    target_data = shell_instance.inventory.get_host(target)
    if not target_data:
        print(f"[!] Error: Host '{target}' not found in inventory.")
        # Provide a helpful hint of what IS available
        available = ", ".join(shell_instance.inventory.list_hosts())
        print(f"    Available hosts: {available}")
        return
    
    hostname = target_data.get('hostname', 'Unknown IP')
    print(f"[*] Connecting to {target} ({hostname}) via SSH...")
    
    try:
        # 2. Connection Attempt
        shell_instance.conn_manager.connect(target, target_data)
        
        # 3. State Update on Success
        shell_instance.active_host = target
        
        # Log the success to the audit trail
        audit_logger.info(f"Successfully connected to '{target}' (IP: {hostname})")
        print(f"[+] Successfully connected to {target}.")
        
    except SwitchAuthError as e:
        audit_logger.warning(f"Authentication failed connecting to '{target}' (IP: {hostname})")
        print(f"[!] Auth Error: {e}")
        
    except SwitchTimeoutError as e:
        audit_logger.warning(f"Connection timeout for '{target}' (IP: {hostname})")
        print(f"[!] Timeout: {e}")
        
    except SwitchConnectionError as e:
        audit_logger.error(f"Connection error for '{target}': {e}")
        print(f"[!] Connection failed: {e}")
        
    except Exception as e:
        audit_logger.error(f"Unexpected error connecting to '{target}': {e}")
        print(f"[!] Unexpected error: {e}")