"""
Output Parser module.

Resolution order per command (see plan.md §10):
    1. Local TextFSM template, if one exists for this vendor/command.
    2. ntc-templates community index, matched by (platform, command).
    3. Raw text, unparsed — returned as-is rather than raising.

`parse` in each vendor's command_map.yaml (see config/command_map/asterfusion.yaml) is one of:
    "raw"                                   -> always return raw text
    "ntc"                                   -> skip local, go straight to ntc-templates
    "<relative/path/to/template.textfsm>"   -> local template; falls back to ntc, then raw,
                                                if the local file is missing or fails to match
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import textfsm

try:
    from ntc_templates.parse import parse_output as ntc_parse_output
    NTC_AVAILABLE = True
except ImportError:
    NTC_AVAILABLE = False

logger = logging.getLogger(__name__)

ParsedResult = Union[List[Dict[str, Any]], str]


class ParserError(Exception):
    """Raised for genuine parsing failures only — never for 'no template matched'.

    A miss at any stage of the fallback chain degrades to raw text instead of raising;
    that behavior lives in parse_command(), not here.
    """


class OutputParser:
    def __init__(self, templates_root: Union[str, Path], default_ntc_platform: str = "cisco_ios"):
        """
        Args:
            templates_root: base directory containing per-vendor local template folders,
                             e.g. src/asterfusion_cli/parsing/templates/ (with asterfusion/,
                             cisco_ios/, etc. subdirectories).
            default_ntc_platform: fallback ntc-templates platform string used ONLY when a
                             caller doesn't supply one explicitly. Kept explicit and logged
                             when used, rather than silently assumed — pass the real vendor's
                             platform (e.g. "huawei_vrp") from the driver whenever possible;
                             see the note on Asterfusion in plan.md §10 before relying on this
                             default for sonic-cli output, since column layouts differ vendor
                             to vendor and a mismatched platform will typically fail to match
                             cleanly rather than raise.
        """
        self.templates_root = Path(templates_root)
        self.default_ntc_platform = default_ntc_platform

    def parse_command(
        self,
        raw_output: str,
        command: str,
        parse_spec: str,
        ntc_platform: Optional[str] = None,
        ntc_command_override: Optional[str] = None,
    ) -> ParsedResult:
        """
        Parse one native command's raw output according to one command_map.yaml entry's
        `parse` value.

        ntc_platform / ntc_command_override let a command_map entry match ntc-templates
        against a DIFFERENT (platform, command) pair than what was actually sent to the
        device — e.g. native "show mac" needs to match ntc's "show mac-address-table"
        pattern to hit an existing Cisco template. These come from an explicit
        `ntc_override:` block in the YAML entry (see command_map schema), never from
        parsing the `parse` string itself — a structured field is validated and fails
        loudly if malformed, where a string mini-language like "ntc:cisco_ios:show x"
        silently gets misread as a local file path (see plan.md notes on this).

        Using an override to force a template from an unrelated vendor onto this
        platform's output is inherently a bet: ntc-templates matches on the command
        string via regex, but a header/column mismatch in the actual data will still
        make the parse fail or return garbage rows even when the command regex matches.
        Verify against real captured output before trusting an override in production —
        don't assume it works just because it doesn't raise.
        """
        if parse_spec == "raw":
            return raw_output.strip()

        if parse_spec != "ntc":
            local_path = self.templates_root / parse_spec
            if local_path.exists():
                try:
                    return self._parse_with_local_template(raw_output, local_path)
                except textfsm.TextFSMError as exc:
                    raise ParserError(
                        f"Local template '{local_path}' failed to parse output for "
                        f"'{command}': {exc}"
                    ) from exc
            logger.info(
                "Local template '%s' not found for '%s' — falling back to ntc-templates.",
                local_path, command,
            )

        # Reached when parse_spec == "ntc", or the local template above was missing.
        match_command = ntc_command_override or command
        if ntc_command_override:
            logger.debug(
                "ntc_override in effect for '%s': matching as '%s' instead.",
                command, ntc_command_override,
            )
        return self._parse_with_ntc(raw_output, match_command, ntc_platform or self.default_ntc_platform)

    def parse_commands(
        self,
        outputs: Dict[str, str],
        parse_spec: str,
        ntc_platform: Optional[str] = None,
        ntc_command_override: Optional[str] = None,
    ) -> Dict[str, ParsedResult]:
        """
        Parse a {native_command: raw_output} dict — one command_map.yaml entry can list
        several native commands. Each is parsed against its OWN command name; outputs are
        never concatenated, since one TextFSM template can't correctly parse two different
        commands' output at once.
        """
        return {
            command: self.parse_command(
                raw,
                command,
                parse_spec,
                ntc_platform=ntc_platform,
                ntc_command_override=ntc_command_override,
            )
            for command, raw in outputs.items()
        }

    def _parse_with_ntc(self, raw_output: str, command: str, platform: str) -> ParsedResult:
        if not NTC_AVAILABLE:
            logger.warning("ntc-templates not installed — returning raw text for '%s'.", command)
            return raw_output.strip()

        try:
            return ntc_parse_output(platform=platform, command=command, data=raw_output)
        except Exception as exc:
            # No matching template (or any other ntc-templates failure) degrades to raw
            # text, matching Netmiko's own use_textfsm=True behavior. This is a fallback,
            # not an error condition, so it's logged rather than raised.
            logger.info(
                "ntc-templates found no match for platform='%s' command='%s' (%s) — "
                "returning raw text.", platform, command, exc,
            )
            return raw_output.strip()

    @staticmethod
    def _parse_with_local_template(raw_output: str, template_path: Path) -> List[Dict[str, Any]]:
        with open(template_path) as f:
            fsm = textfsm.TextFSM(f)
        rows = fsm.ParseText(raw_output)
        return [dict(zip(fsm.header, row)) for row in rows]