"""
Diagnostics Engine module (v2).
Analyzes parsed switch data against predefined playbooks to surface actionable findings.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Callable, Optional
from diakoptis.logging.session_log import audit_logger


class Severity(Enum):
    """Defines the severity level of a diagnostic finding."""
    PASS = "PASS"       # Everything is healthy
    INFO = "INFO"       # General information, no action needed
    WARNING = "WARNING" # Potential issue (e.g., high memory, single CRC error)
    CRITICAL = "CRITICAL" # Hard failure (e.g., link down, BGP peer down)


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
        self._playbooks: Dict[str, Callable] = {}

    def register_playbook(self, command_key: str, playbook_func: Callable) -> None:
        """
        Registers a playbook function to analyze a specific command.
        
        Args:
            command_key: The friendly command name (e.g., 'check_interfaces').
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
            # Silent fallback for multi-switch execution. 
            # The Renderer will just display the aggregated table without spamming INFO messages.
            return []

        try:
            # Execute the playbook and return its findings
            return playbook_func(parsed_data, **kwargs)
        except Exception as e:
            audit_logger.error(f"Playbook execution failed for '{command_key}': {e}")
            return [
                DiagnosticFinding(
                    severity=Severity.WARNING,
                    message=f"Diagnostics failed to run for '{command_key}': {str(e)}"
                )
            ]