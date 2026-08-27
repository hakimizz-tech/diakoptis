"""
Command Resolver module.
Translates friendly CLI commands into formatted native switch commands.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# Import the definitions we made in the configuration layer
from asterfusion.config.command_map import CommandMap, CommandDefinition


class ResolverError(Exception):
    """Base exception for the resolver."""
    pass


class CommandNotFoundError(ResolverError):
    """Raised when a friendly command is not found in the CommandMap."""
    pass


class MissingArgumentError(ResolverError):
    """Raised when a command requires an argument that was not provided."""
    pass


@dataclass
class ResolvedCommand:
    """
    The final, executable package produced by the Resolver.
    """
    friendly_key: str
    native_commands: List[str]
    parse_strategy: str


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
            **kwargs: Dynamic arguments to inject (e.g., interface='Ethernet0').
            
        Returns:
            A ResolvedCommand object ready to be sent to the Connection Manager.
            
        Raises:
            CommandNotFoundError: If the key doesn't exist in the YAML.
            MissingArgumentError: If the YAML expects a variable that wasn't provided.
        """
        definition: Optional[CommandDefinition] = self.command_map.get_command(command_key)
        
        if not definition:
            raise CommandNotFoundError(
                f"Command '{command_key}' is not mapped in command_map.yaml."
            )

        resolved_native_cmds = []
        
        for raw_cmd in definition.native:
            try:
                # Inject the kwargs into the command string.
                # E.g. "show interface {interface}".format(interface="Ethernet0")
                formatted_cmd = raw_cmd.format(**kwargs)
                resolved_native_cmds.append(formatted_cmd)
                
            except KeyError as e:
                # This happens if the YAML has `{interface}` but kwargs didn't include 'interface'
                missing_var = e.args[0]
                raise MissingArgumentError(
                    f"Command '{command_key}' requires the argument '{missing_var}', "
                    f"but it was not provided."
                )
            except IndexError:
                # Catches cases where someone used {} instead of {named_var} in the YAML
                raise ResolverError(
                    f"Command '{command_key}' has invalid formatting in command_map.yaml. "
                    "Always use named variables like {interface} instead of {}."
                )

        return ResolvedCommand(
            friendly_key=command_key,
            native_commands=resolved_native_cmds,
            parse_strategy=definition.parse
        )