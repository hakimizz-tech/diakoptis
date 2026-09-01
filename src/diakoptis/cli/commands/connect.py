"""
Connect command handler (v2).
Handles parsing target expressions and initiating concurrent SSH sessions 
to multiple switches via the Session Pool.
"""

from diakoptis.logging.session_log import audit_logger
from diakoptis.targeting.target_parser import TargetParseError


def execute(args: list[str], shell_instance) -> None:
    """
    Executes the 'connect' command.
    
    Args:
        args: List of string arguments provided by the user (e.g., ['leaf01,leaf02']).
        shell_instance: The diakoptisCLI instance.
    """
    if not args:
        print("[!] Usage: connect <target-expression>")
        print("    Examples:")
        print("      connect lab-leaf01")
        print("      connect lab-leaf01,lab-leaf02")
        print("      connect @core_uplinks")
        print("      connect @role:leaf&@site:nairobi")
        return

    # Join args in case the user typed with spaces (e.g., '@role:leaf & @site:nairobi')
    # We strip whitespace since the TargetParser handles tokenization internally.
    expression = "".join(args)

    # 1. Parse the target expression into a deduplicated list of hostnames
    try:
        targets : list[str] = shell_instance.target_parser.parse(expression)
    except TargetParseError as e:
        print(f"[!] Target Error: {e}")
        # Provide a helpful hint of what IS available if it's a simple, single-host typo
        if not any(char in expression for char in ["@", ",", "&"]):
            available = ", ".join(shell_instance.inventory.list_hosts()[:10]) # Limit to 10 for sanity
            print(f"    Available hosts: {available}...")
        return

    plural = "s" if len(targets) != 1 else ""
    print(f"[*] Resolving credentials and connecting to {len(targets)} host{plural}...")
    
    # 2. Initiate concurrent connections via the Session Pool
    # connect_all returns a dict mapping hostname -> error message (or None if success)
    results = shell_instance.pool.connect_all(
        targets=targets,
        inventory=shell_instance.inventory,
        credentials_mgr=shell_instance.cred_manager
    )
    
    # 3. Report Results
    success_count = 0
    for hostname, error in results.items():
        if error:
            audit_logger.warning(f"Failed to connect to '{hostname}': {error}")
            print(f"[!] Failed to connect to {hostname}: {error}")
        else:
            audit_logger.info(f"Successfully connected to '{hostname}'")
            print(f"[+] Successfully connected to {hostname}.")
            success_count += 1
            
    # 4. Summary
    if success_count > 0:
        print(f"[*] {success_count}/{len(targets)} sessions established.")
    else:
        print("[!] No sessions established.")