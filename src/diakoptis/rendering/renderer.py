"""
Output Renderer module (v2).
Takes aggregated data, raw multi-switch text, and diagnostic findings 
and formats them for the terminal using the 'rich' library.
"""

from typing import Any, Dict, List, Optional, Union
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme

from diakoptis.diagnostics.engine import DiagnosticFinding, Severity

# Define a custom theme for consistent colors across the CLI
custom_theme = Theme({
    "info": "cyan",
    "warning": "bold yellow",
    "critical": "bold red",
    "pass": "bold green",
    "header": "bold magenta",
    "host": "bold cyan"
})


class OutputRenderer:
    def __init__(self):
        """Initializes the Rich console with our custom theme."""
        self.console = Console(theme=custom_theme)

    def display_raw_multi(self, raw_outputs: Dict[str, str], title: str = "Raw Output") -> None:
        """
        Displays raw, unparsed text from multiple switches.
        
        Args:
            raw_outputs: Dict mapping hostname -> raw string output.
            title: The base title for the panels.
        """
        if not raw_outputs:
            self.console.print(f"[warning]No output returned for {title}[/warning]")
            return
            
        for hostname, text in raw_outputs.items():
            if not text.strip():
                text = "<No output returned>"
                
            panel = Panel(
                text.strip(), 
                title=f"{title} - [host]{hostname}[/host]", 
                border_style="blue", 
                expand=False
            )
            self.console.print(panel)
            self.console.print()  # Empty line for spacing

    def display_table(self, data: List[Dict[str, Any]], title: str = "Aggregated Output") -> None:
        """
        Dynamically generates a Rich table from a list of dictionaries.
        Automatically handles both Vertical and Comparison aggregated views.
        
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
            # Highlight the HOST column specifically for vertical aggregation views
            if header.upper() == "HOST":
                table.add_column(header, style="host", justify="left")
            else:
                table.add_column(header, justify="left")

        # Add rows
        for row in data:
            row_values = []
            for h in headers:
                val = str(row.get(h, ""))
                # If this is a comparison view and a switch is explicitly marked "down", 
                # inject a bit of color to make it pop.
                if val.lower() == "down":
                    val = f"[critical]{val}[/critical]"
                row_values.append(val)
                
            table.add_row(*row_values)

        self.console.print(table)
        self.console.print()  # Empty line for spacing

    def display_diagnostics(self, findings: List[DiagnosticFinding]) -> None:
        """
        Renders diagnostic findings with severity-based icons and colors.
        Now accounts for multi-switch host context.
        """
        if not findings:
            self.console.print("[info]No anomalies detected across targeted switches.[/info]")
            self.console.print()
            return

        self.console.print(Text("Diagnostic Findings:", style="bold underline cyan"))
        
        for finding in findings:
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

            # Check if the playbook injected the hostname into the context
            host_prefix = ""
            host = finding.context.get("host")
            if host:
                host_prefix = f"[[host]{host}[/host]] "

            # Print the main finding message
            self.console.print(f"{icon} {host_prefix}[{style}]{finding.message}[/{style}]")
            
            # Print any actionable context below it
            if "action" in finding.context:
                action = finding.context['action']
                self.console.print(f"   ↳ [dim italic]Recommended Action: {action}[/dim italic]")

        self.console.print()

    def display_results(self, 
                        parsed_data: Union[List[Dict[str, Any]], Dict[str, str]], 
                        findings: Optional[List[DiagnosticFinding]] = None, 
                        title: str = "Command Output") -> None:
        """
        Unified orchestrator method. Detects the data shape and routes it to 
        the correct rendering function.
        """
        # 1. Render the Data
        if isinstance(parsed_data, dict):
            # If it's a dict, it means it's unparsed raw text mapping: { "host1": "raw string..." }
            self.display_raw_multi(parsed_data, title=title)
        elif isinstance(parsed_data, list):
            # If it's a list, it's aggregated structured data (vertical or comparison)
            self.display_table(parsed_data, title=title)
        
        # 2. Render the Findings (if provided)
        if findings:
            self.display_diagnostics(findings)