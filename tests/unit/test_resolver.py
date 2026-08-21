"""
Unit tests for the Command Resolver.
Verifies command translation, variable injection, and error handling.
"""

import pytest
import yaml

from asterfusion.config.command_map import CommandMap
from asterfusion.resolver.resolver import (
    CommandResolver,
    CommandNotFoundError,
    MissingArgumentError
)

# Fixtures

@pytest.fixture
def mock_command_map(tmp_path) -> CommandMap:
    """
    Creates a temporary command_map.yaml file with known test data,
    then initializes and returns a CommandMap object.
    """
    config_data = {
        "show_bgp": {
            "description": "Show BGP summary",
            "native": ["show ip bgp summary"],
            "parse": "textfsm:bgp.textfsm"
        },
        "check_interface": {
            "description": "Check a specific interface",
            "native": [
                "show interface {target}",
                "show interface {target} counters"
            ],
            "parse": "textfsm:interface_health.textfsm"
        }
    }
    
    # Write the dictionary to a temporary YAML file
    test_yaml_path = tmp_path / "test_command_map.yaml"
    with open(test_yaml_path, "w") as f:
        yaml.dump(config_data, f)
        
    return CommandMap(filepath=str(test_yaml_path))


@pytest.fixture
def resolver(mock_command_map: CommandMap) -> CommandResolver:
    """Returns an initialized CommandResolver using the mock command map."""
    return CommandResolver(mock_command_map)


# Tests

def test_resolve_static_command(resolver: CommandResolver):
    """Verifies that a command with no variables resolves correctly."""
    resolved = resolver.resolve("show_bgp")
    
    assert resolved.friendly_key == "show_bgp"
    assert len(resolved.native_commands) == 1
    assert resolved.native_commands[0] == "show ip bgp summary"
    assert resolved.parse_strategy == "textfsm:bgp.textfsm"


def test_resolve_parameterized_command(resolver: CommandResolver):
    """Verifies that variables (kwargs) are correctly injected into the native command."""
    resolved = resolver.resolve("check_interface", target="Ethernet4")
    
    assert len(resolved.native_commands) == 2
    assert resolved.native_commands[0] == "show interface Ethernet4"
    assert resolved.native_commands[1] == "show interface Ethernet4 counters"


def test_resolve_unknown_command(resolver: CommandResolver):
    """Verifies that requesting an unmapped command raises CommandNotFoundError."""
    with pytest.raises(CommandNotFoundError) as exc_info:
        resolver.resolve("show_magic_unicorns")
        
    assert "not mapped" in str(exc_info.value)


def test_resolve_missing_argument(resolver: CommandResolver):
    """Verifies that failing to provide a required variable raises MissingArgumentError."""
    # check_interface requires {target}, but we won't provide it
    with pytest.raises(MissingArgumentError) as exc_info:
        resolver.resolve("check_interface")
        
    assert "requires the argument 'target'" in str(exc_info.value)


def test_resolve_extra_arguments_ignored(resolver: CommandResolver):
    """Verifies that providing extra, unneeded arguments doesn't crash the resolver."""
    resolved = resolver.resolve(
        "check_interface", 
        target="Ethernet0", 
        unrelated_variable="ignore_me"
    )
    
    # It should succeed and just ignore 'unrelated_variable'
    assert resolved.native_commands[0] == "show interface Ethernet0"