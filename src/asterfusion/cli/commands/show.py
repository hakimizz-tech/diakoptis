"""
Show command handler.
Translates user 'show ...' input into a mapped command and executes it.
Falls back to raw execution if the command is not mapped.
"""

from asterfusion.logging.session_log import audit_logger
from asterfusion.resolver.resolver import CommandNotFoundError


def execute(args: list[str], shell_instance) -> None:
    """
    Executes the 'show' command group.
    
    Args:
        args: List of string arguments provided by the user (e.g., ['interfaces']).
        shell_instance: The AsterfusionCLI instance.
    """
    if not args:
        print("[!] Usage: show <feature> [options]")
        print("    Example: show interfaces")
        print("    Example: show interface errors")
        return

    # Check if we have an active SSH session
    if not shell_instance.active_host:
        print("[!] Cannot run 'show': Not connected to a switch.")
        print("    Hint: Use 'connect <host>' first.")
        return

    # Convert the user's arguments into the yaml key format
    # e.g., "show interface errors" -> "show_interface_errors"
    command_key = f"show_{'_'.join(args)}"
    raw_fallback_cmd = f"show {' '.join(args)}"
    title_context = f"Show {' '.join(args).title()} on {shell_instance.active_host}"

    try:
        # 1. Command Resolution
        try:
            mapped_cmd = shell_instance.resolver.resolve(command_key)
            native_commands = mapped_cmd.native_commands
            parse_strategy = mapped_cmd.parse_strategy
            
        except CommandNotFoundError:
            # Pass-Through Mode
            print(f"[*] '{command_key}' not mapped in config. Passing raw command to switch...")
            native_commands = [raw_fallback_cmd]
            parse_strategy = "raw"  # Force raw text output
            
        # Log the execution to the background audit file
        audit_logger.info(
            f"Executing '{command_key}' on '{shell_instance.active_host}'. "
            f"Native commands: {native_commands}"
        )
        
        # 2. Execution via Netmiko
        print(f"[*] Fetching data from {shell_instance.active_host}...")
        raw_outputs = shell_instance.conn_manager.send_commands(native_commands)
        
        # 3. Parsing (TextFSM or Raw)
        parsed_data = shell_instance.parser.parse_multiple(raw_outputs, parse_strategy)
        
        # 4. Rendering (Rich Tables or Raw Panel)
        # We don't run the diagnostics engine here; 'show' is just for displaying data.
        shell_instance.renderer.display_results(
            parsed_data=parsed_data, 
            title=title_context
        )
        
    except Exception as e:
        print(f"[!] Error executing 'show': {e}")
        audit_logger.error(f"Error during '{command_key}' execution: {e}")