"""
BGP Health Playbook.
Analyzes BGP summary data to detect dropped peers, idle sessions, or routing anomalies.
"""

from typing import List, Dict, Any
from asterfusion.diagnostics.engine import DiagnosticFinding, Severity
from asterfusion.diagnostics.playbooks.registry import playbook

@playbook("check_bgp", "check_bgp_neighbor")
def analyze(parsed_data: List[Dict[str, Any]], **kwargs) -> List[DiagnosticFinding]:
    """
    Executes the BGP health diagnostic rules.
    
    Args:
        parsed_data: The list of BGP neighbor dictionaries from the OutputParser.
        **kwargs: Optional context, such as `neighbor_ip` to filter for a specific peer.
        
    Returns:
        A list of DiagnosticFindings.
    """
    findings: List[DiagnosticFinding] = []
    
    # If the user ran `check bgp neighbor 10.0.0.1`, cmd_kwargs passed this as `neighbor_ip`.
    target_neighbor = kwargs.get("neighbor_ip")

    # Guard clause in case the parser failed to return a list
    if not isinstance(parsed_data, list):
        return [
            DiagnosticFinding(
                severity=Severity.WARNING, 
                message="Playbook received invalid data format. Expected a list of BGP peers."
            )
        ]

    if not parsed_data:
        return [
            DiagnosticFinding(
                severity=Severity.INFO,
                message="No BGP configuration or peers found on this switch."
            )
        ]

    for bgp_data in parsed_data:
        neighbor = bgp_data.get("NEIGHBOR", "Unknown")

        # If a specific target was requested, skip all other peers
        if target_neighbor and neighbor != target_neighbor:
            continue

        # In SONiC, the column is usually 'State/PfxRcd'
        # If it's a number, the session is established. If it's text, it's in a transitional/down state.
        state_or_pfx = bgp_data.get("STATE_PFX_RCD", "").strip()
        uptime = bgp_data.get("UP_DOWN", "Unknown")
        remote_as = bgp_data.get("AS", "Unknown")

        # Rule 1: Established & Healthy (State is a digit)
        if state_or_pfx.isdigit():
            pfx_count = int(state_or_pfx)
            if pfx_count == 0:
                findings.append(
                    DiagnosticFinding(
                        severity=Severity.WARNING,
                        message=f"BGP peer {neighbor} (AS {remote_as}) is ESTABLISHED but receiving 0 prefixes.",
                        context={"neighbor": neighbor, "uptime": uptime, "action": "Verify route maps or prefix lists."}
                    )
                )
            else:
                findings.append(
                    DiagnosticFinding(
                        severity=Severity.PASS,
                        message=f"BGP peer {neighbor} is ESTABLISHED and receiving {pfx_count} prefixes.",
                        context={"neighbor": neighbor, "uptime": uptime}
                    )
                )

        # Rule 2: Session Administratively Down 
        elif "Admin" in state_or_pfx or "Shut" in state_or_pfx:
            findings.append(
                DiagnosticFinding(
                    severity=Severity.INFO,
                    message=f"BGP peer {neighbor} is administratively shut down.",
                    context={"neighbor": neighbor}
                )
            )

        # Rule 3: Session Down / Transitional (Idle, Active, Connect) 
        else:
            findings.append(
                DiagnosticFinding(
                    severity=Severity.CRITICAL,
                    message=f"BGP peer {neighbor} is DOWN. State is '{state_or_pfx}'.",
                    context={
                        "neighbor": neighbor,
                        "remote_as": remote_as,
                        "action": "Check Layer 3 reachability, password matching, or AS configuration."
                    }
                )
            )

    # If the user asked for a specific peer but we didn't find it
    if target_neighbor and not findings:
        findings.append(
            DiagnosticFinding(
                severity=Severity.WARNING,
                message=f"BGP peer '{target_neighbor}' was not found in the routing table.",
                context={"target": target_neighbor}
            )
        )

    return findings