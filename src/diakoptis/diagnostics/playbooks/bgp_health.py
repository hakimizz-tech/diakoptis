"""
BGP Health Playbook.
Analyzes BGP summary data to detect dropped peers, idle sessions, or routing anomalies.
"""

from typing import List, Dict, Any
from diakoptis.diagnostics.engine import DiagnosticFinding, Severity
from diakoptis.diagnostics.playbooks.registry import playbook

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
    
    # The CLI passes the positional target as `target`; older direct playbook callers may
    # pass `neighbor_ip` explicitly. Accept either name for compatibility.
    target_neighbor = kwargs.get("neighbor_ip") or kwargs.get("target")

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
        neighbor = (
            bgp_data.get("NEIGHBOR")
            or bgp_data.get("bgp_neighbor")
            or bgp_data.get("neighbor")
            or "Unknown"
        )

        # If a specific target was requested, skip all other peers
        if target_neighbor and neighbor != target_neighbor:
            continue

        # ntc-templates uses 'state_or_prefixes_received' while some older fixtures and
        # raw vendor output use 'STATE_PFX_RCD' / 'AS' / 'UP_DOWN'. Accept both shapes.
        state_or_pfx = (
            str(bgp_data.get("STATE_PFX_RCD")
                or bgp_data.get("state_or_prefixes_received")
                or bgp_data.get("STATE_OR_PREFIXES_RECEIVED")
                or "").strip()
        )
        uptime = str(bgp_data.get("UP_DOWN") or bgp_data.get("up_down") or "Unknown")
        remote_as = str(bgp_data.get("AS") or bgp_data.get("neighbor_as") or bgp_data.get("AS_NUMBER") or "Unknown")

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