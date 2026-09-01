"""
Show command handler (v2).
Translates user 'show ...' input into a mapped command, executes it concurrently 
across all active switches via the SessionPool, and aggregates the results.
"""

from diakoptis.logging.session_log import audit_logger
from diakoptis.resolver.resolver import CommandNotFoundError


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
    raw_fallback_cmd = f"show {' '.join(args)}"
    
    # Format a nice title context based on how many hosts we are querying
    hosts = shell_instance.pool.active_hostnames
    host_context = f"{len(hosts)} host(s)" if len(hosts) > 2 else ", ".join(hosts)
    title_context = f"Show {' '.join(args).title()} across {host_context}"

    try:
        mapped_cmd = None

        # 1. Command Resolution
        try:
            mapped_cmd = shell_instance.resolver.resolve(command_key)
            native_commands = mapped_cmd.native_commands
            parse_strategy = mapped_cmd.parse_strategy

        except CommandNotFoundError:
            # Pass-Through Mode
            print(f"[*] '{command_key}' not mapped in config. Passing raw command...")
            native_commands = [raw_fallback_cmd]
            parse_strategy = "raw"

        audit_logger.info(
            f"Executing '{command_key}' across {len(hosts)} hosts. "
            f"Native commands: {native_commands}"
        )

        # 2. Fan-Out Execution via Session Pool
        print(f"[*] Fetching data concurrently from {host_context}...")
        raw_multi_outputs = shell_instance.pool.send_commands_all(native_commands)

        # 3. Parsing (per-switch)
        parsed_results = {}
        raw_flattened = {}

        for hostname, raw_dict in raw_multi_outputs.items():
            combined_raw = "\n".join(raw_dict.values())
            raw_flattened[hostname] = combined_raw

            if parse_strategy != "raw" and mapped_cmd:
                try:
                    override = mapped_cmd.ntc_override
                    ntc_platform = override.get("platform") if override else None
                    ntc_command_override = override.get("command") if override else None

                    if len(native_commands) == 1:
                        command = native_commands[0]
                        parsed_data = shell_instance.parser.parse_command(
                            raw_dict[command],
                            command,
                            parse_strategy,
                            ntc_platform=ntc_platform,
                            ntc_command_override=ntc_command_override,
                        )
                    else:
                        parsed_outputs = shell_instance.parser.parse_commands(
                            raw_dict,
                            parse_strategy,
                            ntc_platform=ntc_platform,
                            ntc_command_override=ntc_command_override,
                        )
                        parsed_rows = []
                        for command_result in parsed_outputs.values():
                            if not isinstance(command_result, list):
                                raise ValueError(
                                    "Parser returned raw text for a command requiring structured data."
                                )
                            parsed_rows.extend(command_result)
                        parsed_data = parsed_rows

                    if not isinstance(parsed_data, list):
                        raise ValueError(
                            "Parser returned raw text for a command requiring structured data."
                        )
                    parsed_results[hostname] = parsed_data
                except Exception as e:
                    audit_logger.warning(f"Parsing failed for {hostname}: {e}")
                    parsed_results[hostname] = [{"PARSE_ERROR": str(e)}]
        
        # 4. Aggregation & Rendering
        if parse_strategy == "raw":
            # The Renderer's display_raw_multi expects a Dict[str, str] mapping hostname -> text
            shell_instance.renderer.display_results(
                parsed_data=raw_flattened, 
                title=title_context
            )
        else:
            # The Aggregator combines { "hostA": [row1], "hostB": [row2] } into one big table list
            aggregated_data = shell_instance.aggregator.aggregate_vertical(parsed_results)
            shell_instance.renderer.display_results(
                parsed_data=aggregated_data, 
                title=title_context
            )
        
    except Exception as e:
        print(f"[!] Error executing 'show': {e}")
        audit_logger.error(f"Error during '{command_key}' execution: {e}")