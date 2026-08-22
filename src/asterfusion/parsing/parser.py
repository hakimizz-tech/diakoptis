"""
Output Parser module.
Dispatches raw switch CLI output to the correct TextFSM template based on the mapping.
Defaults to 'ntc-templates' if a local template is not found.
"""

import textfsm
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Attempt to import ntc-templates for fallback support
try:
    import ntc_templates
    from ntc_templates.parse import parse_output
    NTC_AVAILABLE = True
    # Find the directory where NTC stores its raw .textfsm files
    NTC_TEMPLATES_DIR = Path(ntc_templates.__file__).parent / "templates"
except ImportError:
    NTC_AVAILABLE = False
    NTC_TEMPLATES_DIR = None


class ParserError(Exception):
    """Base exception for parsing errors."""
    pass


class TemplateNotFoundError(ParserError):
    """Raised when a specified TextFSM template cannot be found locally or via NTC."""
    pass


class OutputParser:
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initializes the parser.
        
        Args:
            templates_dir: Optional override for the templates directory. 
                           Defaults to the 'templates' folder relative to this file.
        """
        if templates_dir:
            self.templates_dir = Path(templates_dir)
        else:
            self.templates_dir = Path(__file__).parent / "templates"
            
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def parse(self, raw_output: str, strategy: str) -> Union[List[Dict[str, Any]], str]:
        """
        Parses a single raw text string based on the given strategy.
        
        Args:
            raw_output: The raw text from the switch.
            strategy: 'raw', 'textfsm:<filename.textfsm>', or 'ntc:<command>'.
            
        Returns:
            A list of dictionaries if parsed via TextFSM/NTC, or the raw string if 'raw'.
        """
        strategy_lower = strategy.lower()

        if strategy_lower == "raw":
            return raw_output.strip()

        # 1. TextFSM Strategy (Local file with fallback to NTC directory)
        if strategy_lower.startswith("textfsm:"):
            template_filename = strategy.split(":", 1)[1].strip()
            return self._parse_textfsm(raw_output, template_filename)

        # 2. Native NTC Strategy (e.g., "ntc:show ip bgp summary" or "ntc:cisco_ios:show ip bgp")
        if strategy_lower.startswith("ntc:"):
            if not NTC_AVAILABLE:
                raise ParserError("The 'ntc-templates' package is not installed. Run 'pip install ntc-templates'.")
            
            parts = strategy.split(":", 2)
            if len(parts) == 3:
                platform = parts[1].strip()
                command = parts[2].strip()
            else:
                # FRR routing on AsterNOS closely mimics Cisco IOS syntax, 
                # so it is the safest default platform for NTC lookups.
                platform = "cisco_ios"
                command = parts[1].strip()
                
            try:
                return parse_output(platform=platform, command=command, data=raw_output)
            except Exception as e:
                raise ParserError(f"NTC parsing failed for command '{command}': {e}")

        raise ParserError(f"Unknown parse strategy: '{strategy}'. Must be 'raw', 'textfsm:<filename>', or 'ntc:<command>'")

    def parse_multiple(self, raw_outputs: Dict[str, str], strategy: str) -> Union[List[Dict[str, Any]], Dict[str, str]]:
        """
        Handles the dictionary of outputs returned by ConnectionManager.send_commands().
        """
        if strategy.lower() == "raw":
            return raw_outputs

        if not strategy.lower().startswith(("textfsm:", "ntc:")):
            raise ParserError(f"Unknown parse strategy: '{strategy}'")

        # TextFSM state machines process continuous streams of text.
        # We concatenate the output of multiple commands and re-use the main parse logic.
        combined_text = "\n".join(raw_outputs.values())
        parsed_data = self.parse(combined_text, strategy)
        if isinstance(parsed_data, str):
            raise ParserError(f"Strategy '{strategy}' returned raw text unexpectedly")
        return parsed_data

    def _parse_textfsm(self, text: str, template_filename: str) -> List[Dict[str, Any]]:
        """
        Executes the TextFSM engine against the text. Looks locally first, then falls back to NTC.
        """
        template_path = self.templates_dir / template_filename
        
        # The NTC Fallback Logic
        if not template_path.exists() and NTC_TEMPLATES_DIR is not None:
            ntc_fallback_path = NTC_TEMPLATES_DIR / template_filename
            if ntc_fallback_path.exists():
                template_path = ntc_fallback_path

        if not template_path.exists():
            raise TemplateNotFoundError(
                f"TextFSM template '{template_filename}' not found in local templates/ or ntc-templates."
            )

        try:
            with open(template_path, "r") as f:
                fsm = textfsm.TextFSM(f)
                headers = fsm.header
                raw_results = fsm.ParseText(text)
                
                # Zip the headers and the row values together into a dictionary
                structured_data = [dict(zip(headers, row)) for row in raw_results]
                return structured_data
                
        except textfsm.TextFSMError as e:
            raise ParserError(f"TextFSM parsing failed for template '{template_filename}': {e}")