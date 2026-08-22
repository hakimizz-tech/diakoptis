"""
Diagnostics Engine module.
Analyzes parsed switch data against predefined playbooks to surface actionable findings.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Callable, Optional


class Severity(Enum):
    """Defines the severity level of a diagnostic finding."""
    PASS = "PASS"           # Everything is healthy
    INFO = "INFO"           # General information, no action needed
    WARNING = "WARNING"     # Potential issue (e.g., high memory, single CRC error)
    CRITICAL = "CRITICAL"   # Hard failure (e.g., link down, BGP peer down)


@dataclass
class DiagnosticFinding:
    """
    Represents a single actionable insight discovered by the diagnostics engine.
    """
    severity: Severity
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        return f"[{self.severity.name}] {self.message}"


class DiagnosticsEngine:
    def __init__(self):
        """
        Initializes the Diagnostics Engine and registers available playbooks.
        """
        # A registry mapping a command_key to its diagnostic function (playbook)
        # In a larger app, you could dynamically import these using pkgutil or importlib.
        self._playbooks: Dict[str, Callable] = {}
        
        # We will register them dynamically so engine.py doesn't need to be 
        # modified every time you write a new playbook.

    def register_playbook(self, command_key: str, playbook_func: Callable) -> None:
        """
        Registers a playbook function to analyze a specific command.
        
        Args:
            command_key: The friendly command name (e.g., 'check_interface').
            playbook_func: A function that takes (parsed_data, **kwargs) and returns List[DiagnosticFinding].
        """
        self._playbooks[command_key] = playbook_func

    def analyze(self, command_key: str, parsed_data: Any, **kwargs: Any) -> List[DiagnosticFinding]:
        """
        Routes the parsed data to the correct diagnostic playbook.
        
        Args:
            command_key: The friendly command name.
            parsed_data: The structured data returned by the OutputParser.
            **kwargs: Any additional context (like target interface or IP).
            
        Returns:
            A list of DiagnosticFinding objects. Returns an empty list if no playbook exists,
            or if the data is entirely healthy and the playbook doesn't emit PASS findings.
        """
        playbook_func = self._playbooks.get(command_key)
        
        if not playbook_func:
            # If no playbook is registered for this command, just return an INFO finding.
            # This allows the CLI to gracefully fall back to just displaying the raw table.
            return [
                DiagnosticFinding(
                    severity=Severity.INFO,
                    message=f"No automated diagnostic playbook mapped for '{command_key}'. Visual inspection required."
                )
            ]

        try:
            # Execute the playbook and return its findings
            return playbook_func(parsed_data, **kwargs)
        except Exception as e:
            return [
                DiagnosticFinding(
                    severity=Severity.WARNING,
                    message=f"Diagnostics failed to run for '{command_key}': {str(e)}"
                )
            ]