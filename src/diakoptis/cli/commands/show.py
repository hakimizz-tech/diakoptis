"""
Show command handler (v2).
Translates user 'show ...' input into a mapped command, executes it concurrently 
across all active switches via the SessionPool, and aggregates the results.
"""

from diakoptis.logging.session_log import audit_logger
from diakoptis.cli.execution import execute_grouped_command


def execute(args: list[str], shell_instance) -> None:
    """
    Executes the 'show' command group.
    
    Args:
        args: List of string arguments provided by the user (e.g., ['interfaces']).
        shell_instance: The DiakoptisCLI instance.
    """
    if not args:
        print("[!] Usage: show <feature> [options]")
        print("    Example: show interfaces")
        print("    Example: show ip bgp")
        return

    # Check if we have active SSH sessions in the pool
    if not shell_instance.pool.has_active_sessions:
        print("[!] Cannot run 'show': Not connected to any switches.")
        print("    Hint: Use 'connect <target-expr>' first.")
        return

    command_key = f"show_{'_'.join(args)}"
    # Format a nice title context based on how many hosts we are querying
    hosts = shell_instance.pool.active_hostnames
    host_context = f"{len(hosts)} host(s)" if len(hosts) > 2 else ", ".join(hosts)
    title_context = f"Show {' '.join(args).title()} across {host_context}"

    try:
        print(f"[*] Fetching data concurrently from {host_context}...")
        execution = execute_grouped_command(
            shell_instance,
            command_key,
        )
        for hostname, error in execution["errors"].items():
            audit_logger.warning(f"Grouped show failed for {hostname}: {error}")
            print(f"[!] {hostname}: {error}")

        raw_results = {
            hostname: text
            for hostname, text in execution["raw_results"].items()
            if hostname not in execution["parsed_results"]
        }
        if raw_results:
            shell_instance.renderer.display_results(
                raw_results, title=title_context
            )
        if execution["parsed_results"]:
            aggregated_data = shell_instance.aggregator.aggregate_vertical(
                execution["parsed_results"]
            )
            shell_instance.renderer.display_results(aggregated_data, title=title_context)
        
    except Exception as e:
        print(f"[!] Error executing 'show': {e}")
        audit_logger.error(f"Error during '{command_key}' execution: {e}")