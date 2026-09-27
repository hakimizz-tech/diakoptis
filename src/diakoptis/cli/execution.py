"""Shared grouped command execution for CLI handlers."""

from typing import Any, Dict, Optional

from diakoptis.logging.session_log import audit_logger
from diakoptis.parsing.parser import RawParserOutput
from diakoptis.resolver.resolver import CommandNotFoundError


def execute_grouped_command(
    shell_instance,
    command_key: str,
    target: Optional[str] = None,
    allow_raw: bool = True,
) -> Dict[str, Dict[str, Any]]:
    """Resolve, execute, and parse one friendly command per map group.

    Returns dictionaries keyed by hostname. Unsupported commands and parsing or
    execution failures are reported in ``errors`` rather than raised.
    """
    map_groups = shell_instance.command_map_groups()
    driver_groups = {
        map_path: [shell_instance.pool.active_sessions[hostname] for hostname in hostnames]
        for map_path, hostnames in map_groups.items()
    }
    commands_by_group = {}
    command_specs = {}
    errors: Dict[str, str] = {}

    for map_path, hostnames in map_groups.items():
        resolver = shell_instance.command_resolvers[map_path]
        try:
            command_specs[map_path] = resolver.resolve(command_key, target=target)
            commands_by_group[map_path] = command_specs[map_path].native_commands
        except CommandNotFoundError:
            for hostname in hostnames:
                errors[hostname] = (
                    f"Command '{command_key}' is not available for vendor map "
                    f"{map_path.stem}."
                )
        except Exception as exc:
            for hostname in hostnames:
                errors[hostname] = f"Command resolution failed for {map_path.stem}: {exc}"

    if not commands_by_group:
        return {"parsed_results": {}, "raw_results": {}, "errors": errors}

    active_driver_groups = {
        map_path: driver_groups[map_path]
        for map_path in commands_by_group
    }
    raw_outputs = shell_instance.pool.send_commands_by_group(
        active_driver_groups, commands_by_group
    )

    parsed_results = {}
    raw_results = {}
    for map_path, hostnames in map_groups.items():
        if map_path not in command_specs:
            continue
        command = command_specs[map_path]
        parse_strategy = command.parse_strategy
        for hostname in hostnames:
            raw = raw_outputs.get(hostname, {})
            combined_raw = "\n".join(raw.values()) if isinstance(raw, dict) else str(raw)
            raw_results[hostname] = combined_raw

            execution_error = next(
                (
                    value
                    for value in raw.values()
                    if isinstance(value, str)
                    and (
                        value.startswith("Driver execution error:")
                        or value.startswith("Error executing command:")
                    )
                ),
                None,
            ) if isinstance(raw, dict) else None
            context = (
                f"vendor_map={map_path.stem} native_commands={command.native_commands} "
                f"parser_platform={getattr(command, 'ntc_platform', map_path.stem)}"
            )
            if execution_error:
                errors[hostname] = f"Command execution failure ({context}): {execution_error}"
                audit_logger.error("%s: %s", context, errors[hostname])
                continue

            if parse_strategy == "raw":
                if allow_raw:
                    continue
                errors[hostname] = (
                    f"Parser returned raw text ({context}) for command '{command_key}'."
                )
                continue

            parsed_data = None
            try:
                override = command.ntc_override
                ntc_platform = override.get("platform") if override else command.ntc_platform
                ntc_command_override = override.get("command") if override else None
                native_commands = command.native_commands

                if len(native_commands) == 1:
                    parsed_data = shell_instance.parser.parse_command(
                        raw[native_commands[0]],
                        native_commands[0],
                        parse_strategy,
                        ntc_platform=ntc_platform,
                        ntc_command_override=ntc_command_override,
                    )
                else:
                    parsed_outputs = shell_instance.parser.parse_commands(
                        raw,
                        parse_strategy,
                        ntc_platform=ntc_platform,
                        ntc_command_override=ntc_command_override,
                    )
                    parsed_data = []
                    for command_result in parsed_outputs.values():
                        if not isinstance(command_result, list):
                            reason = getattr(command_result, "reason", "parser returned raw text")
                            raise ValueError(f"{reason} ({context})")
                        parsed_data.extend(command_result)

                if not isinstance(parsed_data, list):
                    reason = getattr(parsed_data, "reason", "parser returned raw text")
                    raise ValueError(f"{reason} ({context})")
                parsed_results[hostname] = parsed_data
            except Exception as exc:
                errors[hostname] = str(exc)
                if isinstance(parsed_data, RawParserOutput):
                    errors[hostname] = f"{parsed_data.reason} ({context})"
                audit_logger.error(
                    "Parser failure for host=%s %s: %s",
                    hostname,
                    context,
                    errors[hostname],
                )

    return {
        "parsed_results": parsed_results,
        "raw_results": raw_results,
        "errors": errors,
    }
