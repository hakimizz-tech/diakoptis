"""
Output Renderer module.
Takes raw data, parsed data, and diagnostic findings and formats them
for the terminal using the 'rich' library.
"""

from typing import Any, Dict, List, Optional, Union
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme

# Import our diagnostic models to colorize them appropriately
from asterfusion.diagnostics.engine import DiagnosticFinding, Severity

# Define a custom theme for consistent colors across the CLI
custom_theme = Theme({
    "info": "cyan",
    "warning": "bold yellow",
    "critical": "bold red",
    "pass": "bold green",
    "header": "bold magenta"
})


class OutputRenderer:
    def __init__(self):
        """Initializes the Rich console with our custom theme."""
        self.console = Console(theme=custom_theme)

    def display_raw(self, output: str, title: str = "Raw Output") -> None:
        """
        Displays raw, unparsed text from the switch inside a neat panel.
        
        Args:
            output: The raw text string.
            title: The title for the panel.
        """
        if not output.strip():
            self.console.print(f"[warning]No output returned for {title}[/warning]")
            return
            
        panel = Panel(output.strip(), title=title, border_style="blue", expand=False)
        self.console.print(panel)
        self.console.print()  # Empty line for spacing

    def display_table(self, data: List[Dict[str, Any]], title: str = "Parsed Output") -> None:
        """
        Dynamically generates a Rich table from a list of dictionaries (TextFSM output).
        
        Args:
            data: A list of dictionaries representing rows of data.
            title: The title of the table.
        """
        if not data:
            self.console.print(f"[warning]No parsed data available for {title}[/warning]")
            return

        # Create the table
        table = Table(title=title, show_header=True, header_style="header")

        # Extract column headers from the keys of the first dictionary
        headers = list(data[0].keys())
        for header in headers:
            table.add_column(header, justify="left")

        # Add rows
        for row in data:
            # Convert all values to strings for rendering, providing an empty string for None
            row_values = [str(row.get(h, "")) for h in headers]
            table.add_row(*row_values)

        self.console.print(table)
        self.console.print()  # Empty line for spacing

    def display_diagnostics(self, findings: List[DiagnosticFinding]) -> None:
        """
        Renders diagnostic findings with severity-based icons and colors.
        
        Args:
            findings: A list of DiagnosticFinding objects from the DiagnosticsEngine.
        """
        if not findings:
            self.console.print("[info]No diagnostics available or playbook returned empty.[/info]")
            self.console.print()
            return

        self.console.print(Text("Diagnostic Findings:", style="bold underline cyan"))
        
        for finding in findings:
            # Map Severity to icons and Rich styles
            if finding.severity == Severity.CRITICAL:
                icon = "❌"
                style = "critical"
            elif finding.severity == Severity.WARNING:
                icon = "⚠️ "
                style = "warning"
            elif finding.severity == Severity.PASS:
                icon = "✅"
                style = "pass"
            else: # INFO
                icon = "ℹ️ "
                style = "info"

            # Print the main finding message
            self.console.print(f"{icon} [{style}]{finding.message}[/{style}]")
            
            # Print any actionable context below it
            if "action" in finding.context:
                action = finding.context['action']
                self.console.print(f"   ↳ [dim italic]Recommended Action: {action}[/dim italic]")

        self.console.print()  # Empty line for spacing

    def display_results(self, 
                        parsed_data: Union[List[Dict[str, Any]], str], 
                        findings: Optional[List[DiagnosticFinding]] = None, 
                        title: str = "Command Output") -> None:
        """
        Unified method to display either raw text or a table, followed by 
        optional diagnostic findings.
        """
        # 1. Render the Data
        if isinstance(parsed_data, str):
            self.display_raw(parsed_data, title=title)
        elif isinstance(parsed_data, list):
            self.display_table(parsed_data, title=title)
        
        # 2. Render the Findings (if provided)
        if findings:
            self.display_diagnostics(findings)