"""
Unit tests for the Output Parser.
Verifies raw text pass-through, TextFSM state machine execution, and error handling.
"""

import pytest
from pathlib import Path

from asterfusion.parsing.parser import (
    OutputParser,
    ParserError,
    TemplateNotFoundError
)

# Fixtures

@pytest.fixture
def parser() -> OutputParser:
    """Returns an initialized OutputParser using the real templates directory."""
    # Instantiating without arguments automatically points it to 
    # src/asterfusion_cli/parsing/templates/
    return OutputParser()


@pytest.fixture
def interface_fixture_text() -> str:
    """Loads the mock raw CLI output from the fixtures folder."""
    # Navigate relative to this test file: tests/unit -> tests/fixtures/...
    fixture_path = Path(__file__).parent.parent / "fixtures" / "raw_outputs" / "show_interface_status.txt"
    
    with open(fixture_path, "r") as f:
        return f.read()


# Tests

def test_parse_raw_strategy(parser: OutputParser):
    """Verifies that the 'raw' strategy returns the exact string unmodified."""
    raw_input = "Line 1\nLine 2\n  Line 3"
    result = parser.parse(raw_input, strategy="raw")
    
    assert result == raw_input.strip()


def test_parse_multiple_raw_strategy(parser: OutputParser):
    """Verifies that parsing a dictionary of raw outputs returns the dictionary unmodified."""
    raw_dict = {
        "show clock": "14:00:00 PST",
        "show version": "AsterNOS v3.1"
    }
    result = parser.parse_multiple(raw_dict, strategy="raw")
    
    assert result == raw_dict


def test_parse_textfsm_success(parser: OutputParser, interface_fixture_text: str):
    """
    Verifies that the TextFSM engine successfully extracts rows and variables
    from a block of unstructured text using our custom SONiC template.
    """
    strategy = "textfsm:sonic_show_interface_status.textfsm"
    
    # Act
    parsed_data = parser.parse(interface_fixture_text, strategy)
    
    # Assert
    assert isinstance(parsed_data, list)
    assert len(parsed_data) == 4  # The fixture has exactly 4 interfaces
    
    # Check the first row (Ethernet0 - fully healthy)
    assert parsed_data[0]["INTERFACE"] == "Ethernet0"
    assert parsed_data[0]["SPEED"] == "100G"
    assert parsed_data[0]["OPER_STATUS"] == "up"
    assert parsed_data[0]["ADMIN_STATUS"] == "up"
    
    # Check the second row (Ethernet4 - L1/L2 failure)
    assert parsed_data[1]["INTERFACE"] == "Ethernet4"
    assert parsed_data[1]["OPER_STATUS"] == "down"
    
    # Check the third row (Ethernet8 - administratively down)
    assert parsed_data[2]["INTERFACE"] == "Ethernet8"
    assert parsed_data[2]["ADMIN_STATUS"] == "down"


def test_parse_textfsm_missing_template(parser: OutputParser):
    """Verifies that requesting a non-existent template raises TemplateNotFoundError."""
    strategy = "textfsm:this_template_does_not_exist.textfsm"
    
    with pytest.raises(TemplateNotFoundError) as exc_info:
        parser.parse("some text", strategy)
        
    assert "not found" in str(exc_info.value)


def test_parse_unknown_strategy(parser: OutputParser):
    """Verifies that providing an invalid strategy string raises a ParserError."""
    with pytest.raises(ParserError) as exc_info:
        parser.parse("some text", strategy="magic:template.json")
        
    assert "Unknown parse strategy" in str(exc_info.value)