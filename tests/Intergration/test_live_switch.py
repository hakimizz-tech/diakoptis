"""
Live Switch Integration Tests.
Tests the actual Netmiko connection and execution against real hardware.

These tests are SKIPPED by default to prevent CI/CD pipeline failures.
To run them locally against your lab switch, execute:
    export ASTER_CLI_LIVE_TEST=1
    pytest tests/integration/test_live_switch.py
"""

import os
import pytest
from typing import Dict, Any

from asterfusion.connection.manager import ConnectionManager
from asterfusion.config.inventory import Inventory
from asterfusion.connection.exceptions import SwitchAuthError, SwitchTimeoutError

# Pytest Module-Level Markers
# Applies to every test in this file. Skips unless ASTER_CLI_LIVE_TEST is set.

pytestmark = pytest.mark.skipif(
    not os.getenv("ASTER_CLI_LIVE_TEST"),
    reason="Live tests disabled. Set ASTER_CLI_LIVE_TEST=1 to enable."
)


@pytest.fixture(scope="module")
def target_host() -> str:
    """The name of the host in inventory.yaml to test against."""
    return "lab-leaf01"


@pytest.fixture(scope="module")
def target_data(target_host: str) -> Dict[str, Any]:
    """Loads the real connection dictionary from the local inventory."""
    inventory = Inventory()
    data = inventory.get_host(target_host)
    
    if not data:
        pytest.skip(f"Host '{target_host}' not found in inventory.yaml. Cannot run live test.")
        
    return data


def test_live_connection_and_disconnect(target_host: str, target_data: Dict[str, Any]):
    """
    Tests that the ConnectionManager can successfully negotiate SSH, 
    elevate privileges (if a secret is provided), and close gracefully.
    """
    manager = ConnectionManager()
    
    try:
        # Act
        manager.connect(target_host, target_data)
        
        # Assert
        assert manager.is_connected is True
        assert manager.active_host_name == target_host
        
    finally:
        # Cleanup
        manager.disconnect()
        assert manager.is_connected is False


def test_live_send_command(target_host: str, target_data: Dict[str, Any]):
    """
    Tests sending a basic, non-disruptive command to the live switch
    and verifies that raw string output is returned.
    """
    manager = ConnectionManager()
    
    try:
        manager.connect(target_host, target_data)
        
        # Act
        results = manager.send_commands(["show version", "show clock"])
        
        # Assert
        assert "show version" in results
        assert "show clock" in results
        
        # The output should be a reasonably sized string, not empty
        assert len(results["show version"]) > 20
        assert "Software Version" in results["show version"] or "SONiC" in results["show version"]
        
    finally:
        manager.disconnect()


def test_live_invalid_auth(target_host: str, target_data: Dict[str, Any]):
    """
    Verifies that our custom exceptions properly wrap Netmiko's errors
    when bad credentials are provided.
    """
    manager = ConnectionManager()
    
    # Intentionally corrupt the password
    bad_data = target_data.copy()
    bad_data["password"] = "wrong_password_123"
    
    # Act & Assert
    with pytest.raises(SwitchAuthError):
        manager.connect(target_host, bad_data)