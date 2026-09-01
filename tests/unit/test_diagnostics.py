"""
Unit tests for the Diagnostics Engine and Playbooks.
Verifies playbook routing, error handling, and the logic of network health checks.
"""

import pytest
from typing import List, Dict, Any

from asterfusion.diagnostics.engine import DiagnosticsEngine, Severity, DiagnosticFinding
from asterfusion.diagnostics.playbooks import interface_health, bgp_health


# Fixtures (Mock Parsed Data)

@pytest.fixture
def mock_interface_data() -> List[Dict[str, Any]]:
    return [
        {"INTERFACE": "Ethernet0", "OPER_STATUS": "up", "ADMIN_STATUS": "up", "SPEED": "100G"},
        {"INTERFACE": "Ethernet4", "OPER_STATUS": "down", "ADMIN_STATUS": "up", "SPEED": "100G"},
        {"INTERFACE": "Ethernet8", "OPER_STATUS": "down", "ADMIN_STATUS": "down", "SPEED": "100G"},
    ]

@pytest.fixture
def mock_bgp_data() -> List[Dict[str, Any]]:
    return [
        {"NEIGHBOR": "10.0.0.1", "STATE_PFX_RCD": "15", "UP_DOWN": "01:00", "AS": "65001"},
        {"NEIGHBOR": "10.0.0.2", "STATE_PFX_RCD": "0", "UP_DOWN": "02:00", "AS": "65002"},
        {"NEIGHBOR": "10.0.0.3", "STATE_PFX_RCD": "Idle", "UP_DOWN": "never", "AS": "65003"},
        {"NEIGHBOR": "10.0.0.4", "STATE_PFX_RCD": "Admin", "UP_DOWN": "never", "AS": "65004"},
    ]

@pytest.fixture
def engine() -> DiagnosticsEngine:
    engine = DiagnosticsEngine()
    engine.register_playbook("check_interface", interface_health.analyze)
    engine.register_playbook("check_bgp", bgp_health.analyze)
    return engine


# Engine Core Tests

def test_engine_unmapped_command(engine: DiagnosticsEngine):
    """Verifies the engine gracefully falls back when a command has no playbook."""
    findings = engine.analyze("check_vlan", [{"vlan": 10}])
    
    assert len(findings) == 1
    assert findings[0].severity == Severity.INFO
    assert "No automated diagnostic playbook mapped" in findings[0].message


def test_engine_playbook_crash(engine: DiagnosticsEngine):
    """Verifies the engine catches exceptions thrown by a buggy playbook."""
    def buggy_playbook(data, **kwargs):
        raise ValueError("I crashed!")
        
    engine.register_playbook("buggy_cmd", buggy_playbook)
    findings = engine.analyze("buggy_cmd", [])
    
    assert len(findings) == 1
    assert findings[0].severity == Severity.WARNING
    assert "Diagnostics failed to run" in findings[0].message


# Interface Playbook Tests

def test_interface_health_all_rules(mock_interface_data):
    """Tests that all severity rules trigger correctly for interfaces."""
    findings = interface_health.analyze(mock_interface_data)
    
    assert len(findings) == 3
    
    # Ethernet0: up/up -> PASS
    assert findings[0].severity == Severity.PASS
    assert "healthy" in findings[0].message
    
    # Ethernet4: up/down -> CRITICAL
    assert findings[1].severity == Severity.CRITICAL
    assert "Admin UP but Oper DOWN" in findings[1].message
    
    # Ethernet8: down/down -> INFO
    assert findings[2].severity == Severity.INFO
    assert "administratively shut down" in findings[2].message


def test_interface_health_target_filter(mock_interface_data):
    """Tests the **kwargs filtering for a specific interface."""
    findings = interface_health.analyze(mock_interface_data, target="Ethernet4")
    
    assert len(findings) == 1
    assert findings[0].severity == Severity.CRITICAL
    assert "Ethernet4" in findings[0].message


def test_interface_health_target_not_found(mock_interface_data):
    """Tests when a user requests an interface that doesn't exist."""
    findings = interface_health.analyze(mock_interface_data, target="Ethernet99")
    
    assert len(findings) == 1
    assert findings[0].severity == Severity.WARNING
    assert "not found in the switch output" in findings[0].message


# BGP Playbook Tests

def test_bgp_health_all_rules(mock_bgp_data):
    """Tests that all severity rules trigger correctly for BGP neighbors."""
    findings = bgp_health.analyze(mock_bgp_data)
    
    assert len(findings) == 4
    
    # 10.0.0.1: 15 prefixes -> PASS
    assert findings[0].severity == Severity.PASS
    assert "receiving 15 prefixes" in findings[0].message
    
    # 10.0.0.2: 0 prefixes -> WARNING
    assert findings[1].severity == Severity.WARNING
    assert "receiving 0 prefixes" in findings[1].message
    
    # 10.0.0.3: Idle state -> CRITICAL
    assert findings[2].severity == Severity.CRITICAL
    assert "State is 'Idle'" in findings[2].message
    
    # 10.0.0.4: Admin state -> INFO
    assert findings[3].severity == Severity.INFO
    assert "administratively shut down" in findings[3].message


def test_bgp_health_ntc_style_rows():
    """Tests BGP behavior for ntc-templates output keys from `show ip bgp summary`."""
    data = [
        {"bgp_neighbor": "10.120.30.1", "state_or_prefixes_received": "1", "up_down": "00:18:31", "neighbor_as": "64517"},
        {"bgp_neighbor": "10.120.30.2", "state_or_prefixes_received": "0", "up_down": "00:05:00", "neighbor_as": "64518"},
    ]

    findings = bgp_health.analyze(data)

    assert len(findings) == 2
    assert findings[0].severity == Severity.PASS
    assert "10.120.30.1" in findings[0].message
    assert findings[1].severity == Severity.WARNING
    assert "receiving 0 prefixes" in findings[1].message


def test_bgp_health_target_filter_matches_cli_target():
    """Tests that the generic CLI `target` arg is accepted for specific-neighbor lookups."""
    data = [
        {"bgp_neighbor": "10.120.30.1", "state_or_prefixes_received": "1", "up_down": "00:18:31", "neighbor_as": "64517"},
        {"bgp_neighbor": "10.120.30.2", "state_or_prefixes_received": "0", "up_down": "00:05:00", "neighbor_as": "64518"},
    ]

    findings = bgp_health.analyze(data, target="10.120.30.2")

    assert len(findings) == 1
    assert findings[0].severity == Severity.WARNING
    assert "10.120.30.2" in findings[0].message


def test_bgp_health_empty_data():
    """Tests BGP behavior when no neighbors are configured."""
    findings = bgp_health.analyze([])
    
    assert len(findings) == 1
    assert findings[0].severity == Severity.INFO
    assert "No BGP configuration" in findings[0].message