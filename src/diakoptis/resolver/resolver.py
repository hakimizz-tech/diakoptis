"""
Command Resolver module.
Translates friendly CLI commands into formatted native switch commands.
"""

import string
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# Import the definitions we made in the configuration layer
from diakoptis.config.command_map import CommandMap, CommandDefinition


class ResolverError(Exception):
    """Base exception for the resolver."""
    pass


class CommandNotFoundError(ResolverError):
    """Raised when a friendly command is not found in the CommandMap."""
    pass


class MissingArgumentError(ResolverError):
    """Raised when a command requires an argument that was not provided."""
    pass


class UnusedArgumentError(ResolverError):
    """Raised when an argument is provided but the native command does not accept it."""
    pass


@dataclass
class ResolvedCommand:
    """
    The final, executable package produced by the Resolver.
    """
    friendly_key: str
    native_commands: List[str]
    parse_strategy: str
    ntc_override: Optional[Dict[str, str]] = None


class CommandResolver:
    def __init__(self, command_map: CommandMap):
        """
        Initializes the resolver with a loaded CommandMap.
        
        Args:
            command_map: An instantiated CommandMap object containing definitions.
        """
        self.command_map = command_map

    def resolve(self, command_key: str, **kwargs: Any) -> ResolvedCommand:
        """
        Looks up a command and formats its native strings with the provided variables.
        
        Args:
            command_key: The friendly command name (e.g., 'check_interface').
            **kwargs: Dynamic arguments to inject (e.g., target='Ethernet0').
            
        Returns:
            A ResolvedCommand object ready to be sent to the Connection Manager.
            
        Raises:
            CommandNotFoundError: If the key doesn't exist in the YAML.
            MissingArgumentError: If the YAML expects a variable that wasn't provided.
            UnusedArgumentError: If a variable was provided but the YAML doesn't use it.
        """
        definition: Optional[CommandDefinition] = self.command_map.get_command(command_key)
        
        if not definition:
            raise CommandNotFoundError(
                f"Command '{command_key}' is not mapped in command_map.yaml."
            )

        # 1. Analyze the native commands to find exactly what arguments they expect
        expected_args = set()
        formatter = string.Formatter()
        for raw_cmd in definition.native:
            # formatter.parse returns tuples of (literal_text, field_name, format_spec, conversion)
            for _, field_name, _, _ in formatter.parse(raw_cmd):
                if field_name:
                    expected_args.add(field_name)

        # 2. Strict Check: Did we pass arguments the command doesn't need?
        # We ignore kwargs that are None (often passed by default from CLI frameworks)
        provided_args = {k for k, v in kwargs.items() if v is not None}
        unused_args = provided_args - expected_args
        
        if unused_args:
            raise UnusedArgumentError(
                f"Command '{command_key}' does not accept these arguments: {', '.join(unused_args)}. "
                f"Expected: {', '.join(expected_args) if expected_args else 'None'}"
            )

        # 3. Format the commands
        resolved_native_cmds = []
        for raw_cmd in definition.native:
            try:
                formatted_cmd = raw_cmd.format(**kwargs)
                resolved_native_cmds.append(formatted_cmd)
                
            except KeyError as e:
                missing_var = e.args[0]
                raise MissingArgumentError(
                    f"Command '{command_key}' requires the argument '{missing_var}', "
                    f"but it was not provided."
                )
            except IndexError:
                raise ResolverError(
                    f"Command '{command_key}' has invalid formatting in command_map.yaml. "
                    "Always use named variables like {target} instead of {}."
                )

        # 4. Return the fully resolved command, ensuring ntc_override is passed through
        return ResolvedCommand(
            friendly_key=command_key,
            native_commands=resolved_native_cmds,
            parse_strategy=definition.parse,
            # Use getattr safely in case CommandDefinition hasn't fully updated yet
            ntc_override=getattr(definition, 'ntc_override', None) 
        )