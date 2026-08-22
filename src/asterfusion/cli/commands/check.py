"""
Check command handler (v2).
Executes automated diagnostic playbooks concurrently across all active switches.
Pivots the resulting data into a multi-switch comparison table.
"""

from asterfusion.logging.session_log import audit_logger
from asterfusion.resolver.resolver import CommandNotFoundError


def execute(args: list[str], shell_instance) -> None:
    """
    Executes the 'check' command group.
    
    Args:
        args: List of string arguments (e.g., ['interfaces', 'Ethernet4', '--diff']).
        shell_instance: The AsterfusionCLI instance.
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
    target = clean_args[1] if len(clean_args) > 1 else None
    
    command_key = f"check_{feature}"
    
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
        # 2. Command Resolution 
        try:
            # We pass the optional 'target' keyword argument so the Resolver 
            # can inject it into native commands like 'show interface {target}'
            mapped_cmd = shell_instance.resolver.resolve(command_key, target=target)
        except CommandNotFoundError:
            print(f"[!] Diagnostics Error: '{command_key}' is not a registered check command.")
            return

        if mapped_cmd.parse_strategy == "raw":
            print("[!] Diagnostics Error: Cannot run playbooks against 'raw' unparsed text.")
            return

        audit_logger.info(f"Running diagnostics '{command_key}' across {len(hosts)} hosts.")
        print(f"[*] Analyzing '{feature}' across {host_context}...")

        # --- 3. Fan-Out Execution ---
        raw_multi_outputs = shell_instance.pool.send_commands_all(mapped_cmd.native_commands)

        # 4. Parse Data & Run Diagnostics (Per-Switch) 
        parsed_results = {}
        all_findings = []

        for hostname, raw_dict in raw_multi_outputs.items():
            try:
                # Parse
                parsed_data = shell_instance.parser.parse_multiple(raw_dict, mapped_cmd.parse_strategy)
                parsed_results[hostname] = parsed_data
                
                # Diagnose
                findings = shell_instance.diagnostics.analyze(command_key, parsed_data, target=target)
                
                # Tag the findings with the host they came from so the Renderer can label them
                for finding in findings:
                    finding.context['host'] = hostname
                all_findings.extend(findings)
                
            except Exception as e:
                audit_logger.error(f"Diagnostics failed for {hostname}: {e}")
                parsed_results[hostname] = [{"PARSE_ERROR": str(e)}]

        # 5. Aggregation 
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

        # --- 6. Rendering ---
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