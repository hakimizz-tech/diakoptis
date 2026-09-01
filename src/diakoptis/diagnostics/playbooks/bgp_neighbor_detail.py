"""
BGP Neighbor Detail Playbook.
Analyzes detailed BGP neighbor session information.
"""

from typing import List, Dict, Any
from diakoptis.diagnostics.engine import DiagnosticFinding, Severity
from diakoptis.diagnostics.playbooks.registry import playbook

@playbook("check_bgp_neighbor")
def analyze(parsed_data: List[Dict[str, Any]], **kwargs) -> List[DiagnosticFinding]:
    """
    Executes the BGP neighbor detail diagnostic rules.
    
    Args:
        parsed_data: The list of BGP neighbor detail records from the OutputParser.
        **kwargs: Optional context (not used here since detail is single neighbor).
        
    Returns:
        A list of DiagnosticFindings.
    """
    findings: List[DiagnosticFinding] = []

    if not isinstance(parsed_data, list):
        return [
            DiagnosticFinding(
                severity=Severity.WARNING, 
                message="Playbook received invalid data format. Expected a list of BGP neighbor records."
            )
        ]

    if not parsed_data:
        return [
            DiagnosticFinding(
                severity=Severity.INFO,
                message="No BGP neighbor detail found."
            )
        ]

    for record in parsed_data:
        neighbor = record.get("NEIGHBOR") or "Unknown"
        bgp_state = record.get("BGP_STATE") or "Unknown"
        uptime = record.get("UPTIME") or "Unknown"
        prefixes_received = record.get("ACCEPTED_PREFIXES") or "0"
        remote_as = record.get("REMOTE_AS") or "Unknown"
        connections_established = record.get("CONNECTIONS_ESTABLISHED") or "0"
        connections_dropped = record.get("CONNECTIONS_DROPPED") or "0"
        messages_sent = record.get("MESSAGES_SENT") or "0"
        messages_received = record.get("MESSAGES_RECEIVED") or "0"

        # Rule 1: Session state
        if bgp_state.lower() == "established":
            findings.append(
                DiagnosticFinding(
                    severity=Severity.SUCCESS,
                    message=f"BGP neighbor {neighbor} (AS {remote_as}) is ESTABLISHED (up for {uptime}).",
                    context={
                        "neighbor": neighbor,
                        "remote_as": remote_as,
                        "state": bgp_state,
                        "uptime": uptime
                    }
                )
            )
        else:
            findings.append(
                DiagnosticFinding(
                    severity=Severity.CRITICAL,
                    message=f"BGP neighbor {neighbor} (AS {remote_as}) is in state: {bgp_state}",
                    context={"neighbor": neighbor, "action": "Check BGP configuration and network connectivity."}
                )
            )

        # Rule 2: Prefix reception
        try:
            pfx_count = int(str(prefixes_received).strip())
            if pfx_count == 0:
                findings.append(
                    DiagnosticFinding(
                        severity=Severity.WARNING,
                        message=f"BGP neighbor {neighbor} is not sending any prefixes.",
                        context={"neighbor": neighbor, "action": "Verify route maps and redistribution on peer."}
                    )
                )
        except (ValueError, AttributeError):
            pass

        # Rule 3: Flapping (high connection drops)
        try:
            drops = int(str(connections_dropped).strip())
            established = int(str(connections_established).strip())
            if drops > 0 and established > 1:
                findings.append(
                    DiagnosticFinding(
                        severity=Severity.WARNING,
                        message=f"BGP neighbor {neighbor} has flapped {drops} times (established {established} times).",
                        context={"neighbor": neighbor, "action": "Investigate stability and network path."}
                    )
                )
        except (ValueError, AttributeError):
            pass

    return findings
