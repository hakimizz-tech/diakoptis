"""
Output Parser module.
Dispatches raw switch CLI output to the correct TextFSM template based on the mapping.
"""

import textfsm
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class ParserError(Exception):
    """Base exception for parsing errors."""
    pass


class TemplateNotFoundError(ParserError):
    """Raised when a specified TextFSM template cannot be found."""
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
            # Dynamically locate the templates/ folder in the same directory as this file
            self.templates_dir = Path(__file__).parent / "templates"
            
        # Ensure the directory exists (creates it if it doesn't)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def parse(self, raw_output: str, strategy: str) -> Union[List[Dict[str, Any]], str]:
        """
        Parses a single raw text string based on the given strategy.
        
        Args:
            raw_output: The raw text from the switch.
            strategy: 'raw' or 'textfsm:<filename.textfsm>'.
            
        Returns:
            A list of dictionaries if parsed via TextFSM, or the raw string if 'raw'.
        """
        if strategy.lower() == "raw":
            return raw_output.strip()

        if strategy.lower().startswith("textfsm:"):
            # Extract the filename, e.g., "textfsm:sonic_show_interfaces.textfsm" -> "sonic_show_interfaces.textfsm"
            template_filename = strategy.split(":", 1)[1].strip()
            return self._parse_textfsm(raw_output, template_filename)

        raise ParserError(f"Unknown parse strategy: '{strategy}'. Must be 'raw' or 'textfsm:<filename>'")

    def parse_multiple(self, raw_outputs: Dict[str, str], strategy: str) -> Union[List[Dict[str, Any]], Dict[str, str]]:
        """
        Handles the dictionary of outputs returned by ConnectionManager.send_commands().
        
        Args:
            raw_outputs: Dict mapping the command string to its raw output.
            strategy: 'raw' or 'textfsm:<filename.textfsm>'.
            
        Returns:
            If TextFSM: Combined parsed data as a list of dicts.
            If Raw: Returns the original dictionary.
        """
        if strategy.lower() == "raw":
            return raw_outputs

        if not strategy.lower().startswith("textfsm:"):
            raise ParserError(f"Unknown parse strategy: '{strategy}'")

        # TextFSM state machines are designed to process continuous streams of text.
        combined_text = "\n".join(raw_outputs.values())
        template_filename = strategy.split(":", 1)[1].strip()
        return self._parse_textfsm(combined_text, template_filename)

    def _parse_textfsm(self, text: str, template_filename: str) -> List[Dict[str, Any]]:
        """
        Executes the TextFSM engine against the text using the specified template.
        """
        template_path = self.templates_dir / template_filename
        
        if not template_path.exists():
            raise TemplateNotFoundError(
                f"TextFSM template '{template_filename}' not found at {template_path}"
            )

        try:
            with open(template_path, "r") as f:
                fsm = textfsm.TextFSM(f)
                
                # fsm.ParseText returns a list of lists (rows of values).
                # We want a list of dictionaries mapping the header (column names) to the values.
                headers = fsm.header
                raw_results = fsm.ParseText(text)
                
                # Zip the headers and the row values together into a dictionary
                structured_data = [dict(zip(headers, row)) for row in raw_results]
                
                return structured_data
                
        except textfsm.TextFSMError as e:
            raise ParserError(f"TextFSM parsing failed for template '{template_filename}': {e}")