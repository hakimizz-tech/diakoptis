"""Tests for BGP neighbor detail check and diagnostics."""
import pytest
from diakoptis.diagnostics.playbooks.bgp_neighbor_detail import analyze
from diakoptis.parsing.parser import OutputParser


@pytest.fixture
def sample_neighbor_detail():
    """Load sample neighbor detail output."""
    with open("tests/fixtures/raw_outputs/show_ip_bgp_neighbors_detail.txt") as f:
        return f.read()


@pytest.fixture
def output_parser():
    """Instantiate parser with config."""
    return OutputParser(templates_root="src/diakoptis/parsing/templates")


def test_bgp_neighbor_detail_template(sample_neighbor_detail, output_parser):
    """Test that neighbor detail template parses correctly."""
    parsed = output_parser.parse_command(
        sample_neighbor_detail,
        "show ip bgp neighbors 10.120.30.1",
        "asterfusion/sonic_show_ip_bgp_neighbors_detail.textfsm"
    )
    
    assert parsed is not None
    assert len(parsed) == 1
    
    neighbor = parsed[0]
    assert neighbor["NEIGHBOR"] == "10.120.30.1"
    assert neighbor["REMOTE_AS"] == "64517"
    assert neighbor["BGP_STATE"] == "Established"
    assert neighbor["UPTIME"] == "4d21h31m"
    assert neighbor["ACCEPTED_PREFIXES"] == "11"
    assert neighbor["CONNECTIONS_ESTABLISHED"] == "6"
    assert neighbor["CONNECTIONS_DROPPED"] == "5"
    assert neighbor["MESSAGES_SENT"] == "103763"
    assert neighbor["MESSAGES_RECEIVED"] == "103811"


def test_bgp_neighbor_detail_diagnostics(sample_neighbor_detail, output_parser):
    """Test that diagnostics playbook analyzes neighbor detail."""
    parsed = output_parser.parse_command(
        sample_neighbor_detail,
        "show ip bgp neighbors 10.120.30.1",
        "asterfusion/sonic_show_ip_bgp_neighbors_detail.textfsm"
    )
    
    # Run diagnostics
    findings = analyze(parsed)
    
    assert findings is not None
    assert len(findings) > 0
    
    # Should have SUCCESS for established state
    state_finding = next((f for f in findings if "state" in f.message.lower()), None)
    assert state_finding is not None
    assert state_finding.severity.value == "PASS"
    
    # Should have WARNING for flapping (dropped > 0)
    flapping_finding = next((f for f in findings if "flapping" in f.message.lower()), None)
    assert flapping_finding is not None
    assert flapping_finding.severity.value == "WARNING"


def test_bgp_neighbor_established_healthy():
    """Test healthy established neighbor produces only SUCCESS findings."""
    healthy_data = [{
        "NEIGHBOR": "10.0.0.1",
        "REMOTE_AS": "64000",
        "BGP_STATE": "Established",
        "UPTIME": "100d",
        "ACCEPTED_PREFIXES": "100",
        "CONNECTIONS_ESTABLISHED": "1",
        "CONNECTIONS_DROPPED": "0",  # No flapping
        "MESSAGES_SENT": "50000",
        "MESSAGES_RECEIVED": "50000",
    }]
    
    findings = analyze(healthy_data)
    
    assert all(f.severity.value == "PASS" for f in findings), "All findings for healthy neighbor should be PASS"


def test_bgp_neighbor_down_critical():
    """Test down neighbor produces CRITICAL severity."""
    down_data = [{
        "NEIGHBOR": "10.0.0.1",
        "REMOTE_AS": "64000",
        "BGP_STATE": "Idle",  # Not Established
        "UPTIME": "0d",
        "ACCEPTED_PREFIXES": "0",
        "CONNECTIONS_ESTABLISHED": "0",
        "CONNECTIONS_DROPPED": "0",
        "MESSAGES_SENT": "0",
        "MESSAGES_RECEIVED": "0",
    }]
    
    findings = analyze(down_data)
    
    critical_finding = next((f for f in findings if f.severity.value == "CRITICAL"), None)
    assert critical_finding is not None
    assert "Idle" in critical_finding.message


def test_bgp_neighbor_no_prefixes_warning():
    """Test neighbor with zero prefixes produces WARNING."""
    no_prefixes_data = [{
        "NEIGHBOR": "10.0.0.1",
        "REMOTE_AS": "64000",
        "BGP_STATE": "Established",
        "UPTIME": "10d",
        "ACCEPTED_PREFIXES": "0",  # No prefixes
        "CONNECTIONS_ESTABLISHED": "1",
        "CONNECTIONS_DROPPED": "0",
        "MESSAGES_SENT": "10000",
        "MESSAGES_RECEIVED": "10000",
    }]
    
    findings = analyze(no_prefixes_data)
    
    prefix_finding = next((f for f in findings if "prefix" in f.message.lower()), None)
    assert prefix_finding is not None
    assert prefix_finding.severity.value == "WARNING"
