"""
Check command handler.
Translates user 'check ...' input into parameterized diagnostic commands.
"""

from asterfusion.logging.session_log import audit_logger
from asterfusion.resolver.resolver import CommandNotFoundError, MissingArgumentError


def execute(args: list[str], shell_instance) -> None:
    """
    Executes the 'check' command group.
    
    Args:
        args: List of string arguments provided by the user (e.g., ['interface', 'Ethernet0']).
        shell_instance: The AsterfusionCLI instance.
    """
    if not args:
        print("[!] Usage: check <feature> [target]")
        print("    Example: check bgp")
        print("    Example: check interface Ethernet4")
        print("    Example: check bgp neighbor 10.0.0.1")
        return

    # Check if we have an active SSH session
    if not shell_instance.active_host:
        print("[!] Cannot run 'check': Not connected to a switch.")
        print("    Hint: Use 'connect <host>' first.")
        return

    # --- Parameterized Command Resolution ---
    # We need to figure out which part of the input is the command name
    # and which part is the dynamic variable. 
    if len(args) == 1:
        # e.g., "check vlan" -> key: "check_vlan", args: {}
        command_key = f"check_{args[0]}"
        cmd_kwargs = {}
    elif args[0] == "bgp" and args[1] == "neighbor" and len(args) == 3:
        # e.g., "check bgp neighbor 10.0.0.1" -> key: "check_bgp_neighbor", args: {neighbor_ip: ...}
        command_key = "check_bgp_neighbor"
        cmd_kwargs = {"neighbor_ip": args[2]}
    else:
        # e.g., "check interface Ethernet4" -> key: "check_interface", args: {target: ...}
        # Joins everything except the last arg as the command key
        command_key = f"check_{'_'.join(args[:-1])}"
        cmd_kwargs = {"target": args[-1]}

    try:
        # 1. Intent Translation (Resolver)
        # This handles injecting the cmd_kwargs into the native strings internally
        mapped_cmd = shell_instance.resolver.resolve(command_key, **cmd_kwargs)
        
        # Log the intent to the background audit file
        audit_logger.info(
            f"Executing '{command_key}' on '{shell_instance.active_host}'. "
            f"Native commands: {mapped_cmd.native_commands}"
        )
        
        # 2. Execution (Netmiko)
        # Provide a small loading indicator for the user since network calls block
        print(f"[*] Fetching data from {shell_instance.active_host}...")
        raw_outputs = shell_instance.conn_manager.send_commands(mapped_cmd.native_commands)
        
        # 3. Data Extraction (TextFSM)
        parsed_data = shell_instance.parser.parse_multiple(raw_outputs, mapped_cmd.parse_strategy)
        
        # 4. Expert Analysis (Diagnostics Engine)
        findings = shell_instance.diagnostics.analyze(command_key, parsed_data, **cmd_kwargs)
        
        # 5. Presentation (Rich Renderer)
        title_context = f"{command_key.replace('_', ' ').title()} on {shell_instance.active_host}"
        shell_instance.renderer.display_results(
            parsed_data=parsed_data, 
            findings=findings, 
            title=title_context
        )
            
    except CommandNotFoundError:
        print(f"[!] Unmapped check command: '{command_key}'.")
        print("    If this is a valid command, please add it to config/command_map.yaml.")
    except MissingArgumentError as e:
        print(f"[!] Syntax Error: {e}")
    except Exception as e:
        print(f"[!] Error executing '{command_key}': {e}")
        audit_logger.error(f"Error during '{command_key}' execution: {e}")