"""
Check command handler (v2).
Executes automated diagnostic playbooks concurrently across all active switches.
Pivots the resulting data into a multi-switch comparison table.
"""

from diakoptis.logging.session_log import audit_logger
from diakoptis.cli.execution import execute_grouped_command


def execute(args: list[str], shell_instance) -> None:
    """
    Executes the 'check' command group.
    
    Args:
        args: List of string arguments (e.g., ['interfaces', 'Ethernet4', '--diff']).
        shell_instance: The DiakoptisCLI instance.
    """
    if not args:
        print("[!] Usage: check <feature> [target] [--diff]")
        print("    Example: check interfaces")
        print("    Example: check interfaces Ethernet4")
        print("    Example: check bgp --diff")
        return

    if not shell_instance.pool.has_active_sessions:
        print("[!] Cannot run 'check': Not connected to any switches.")
        return

    # 1. Parse CLI Arguments
    diff_only = "--diff" in args
    clean_args = [arg for arg in args if arg != "--diff"]
    
    feature = clean_args[0].lower()
    target = None
    command_key = f"check_{feature}"

    if feature == "bgp" and len(clean_args) > 1:
        second = clean_args[1].lower()
        if second in {"neighbor", "neighbour"}:
            target = clean_args[2] if len(clean_args) > 2 else None
            command_key = "check_bgp_neighbor"
        else:
            target = clean_args[1]
            command_key = "check_bgp"
    elif len(clean_args) > 1:
        target = clean_args[1]
    
    # Determine the primary key for the Comparison Aggregator matrix
    # (In a larger app, this mapping could live in the command_map.yaml)
    primary_key_map = {
        "check_interface": "INTERFACE",
        "check_interfaces": "INTERFACE",
        "check_bgp": "NEIGHBOR",
        "check_bgp_neighbor": "NEIGHBOR",
    }
    primary_key = primary_key_map.get(command_key)

    hosts = shell_instance.pool.active_hostnames
    host_context = f"{len(hosts)} host(s)" if len(hosts) > 2 else ", ".join(hosts)
    title_context = f"Diagnostic: {feature.title()} across {host_context}"

    try:
        audit_logger.info(f"Running diagnostics '{command_key}' across {len(hosts)} hosts.")
        print(f"[*] Analyzing '{feature}' across {host_context}...")

        # 2. Resolve, execute, and parse independently per command-map group.
        execution = execute_grouped_command(
            shell_instance,
            command_key,
            target=target,
            allow_raw=False,
        )
        for hostname, error in execution["errors"].items():
            audit_logger.error(f"Diagnostics failed for {hostname}: {error}")
            print(f"[!] {hostname}: {error}")

        # 3. Run diagnostics for each successfully parsed host.
        parsed_results = execution["parsed_results"]
        all_findings = []
        for hostname, parsed_data in parsed_results.items():
            try:
                findings = shell_instance.diagnostics.analyze(
                    command_key, parsed_data, target=target
                )
                for finding in findings:
                    if not hasattr(finding, "context") or finding.context is None:
                        finding.context = {}
                    finding.context["host"] = hostname
                all_findings.extend(findings)
            except Exception as exc:
                audit_logger.error(f"Diagnostics failed for {hostname}: {exc}")
                execution["errors"][hostname] = str(exc)

        # Aggregation 
        if primary_key:
            # Pivot the data into a multi-column comparison matrix
            aggregated_data = shell_instance.aggregator.aggregate_comparison(
                parsed_results, 
                primary_key=primary_key, 
                diff_only=diff_only
            )
        else:
            # Fallback to standard vertical stacking if we don't know how to pivot this feature
            aggregated_data = shell_instance.aggregator.aggregate_vertical(parsed_results)

        # Rendering 
        if diff_only and not aggregated_data:
            print(f"[+] All {len(hosts)} switches are in identical states (No diffs found).")
            
        shell_instance.renderer.display_results(
            parsed_data=aggregated_data, 
            findings=all_findings, 
            title=title_context
        )

    except Exception as e:
        print(f"[!] Error executing 'check': {e}")
        audit_logger.error(f"Error during '{command_key}' execution: {e}")