"""
Interface Health Playbook.
Analyzes interface state and counters to diagnose Layer 1/2 issues.
"""

from typing import List, Dict, Any
from asterfusion.diagnostics.engine import DiagnosticFinding, Severity

def analyze(parsed_data: List[Dict[str, Any]], **kwargs) -> List[DiagnosticFinding]:
    """
    Executes the interface health diagnostic rules.
    
    Args:
        parsed_data: The list of interface dictionaries from the OutputParser.
        **kwargs: Optional context, such as `target` to filter for a specific interface.
        
    Returns:
        A list of DiagnosticFindings.
    """
    findings: List[DiagnosticFinding] = []
    
    # If the user ran `check interface Ethernet0`, cmd_kwargs passed this as `target`.
    target_interface = kwargs.get("target")

    # Guard clause in case the parser failed to return a list
    if not isinstance(parsed_data, list):
        return [
            DiagnosticFinding(
                severity=Severity.WARNING, 
                message="Playbook received invalid data format. Expected a list of interfaces."
            )
        ]

    for intf_data in parsed_data:
        name = intf_data.get("INTERFACE", "Unknown")

        # If a specific target was requested, skip all other interfaces
        if target_interface and name.lower() != target_interface.lower():
            continue

        admin = intf_data.get("ADMIN_STATUS", "").lower()
        oper = intf_data.get("OPER_STATUS", "").lower()
        speed = intf_data.get("SPEED", "Unknown")

        # Rule 1: Admin UP, Oper DOWN (Physical / L1 Issue) 
        if admin == "up" and oper == "down":
            findings.append(
                DiagnosticFinding(
                    severity=Severity.CRITICAL,
                    message=f"Interface {name} is Admin UP but Oper DOWN.",
                    context={
                        "interface": name, 
                        "speed": speed,
                        "action": "Check physical cable, transceiver, or remote neighbor port state."
                    }
                )
            )
            
        # Rule 2: Healthy 
        elif admin == "up" and oper == "up":
            findings.append(
                DiagnosticFinding(
                    severity=Severity.PASS,
                    message=f"Interface {name} is healthy and linked at {speed}.",
                    context={"interface": name}
                )
            )
            
        # Admin DOWN (Expected)
        elif admin == "down":
            findings.append(
                DiagnosticFinding(
                    severity=Severity.INFO,
                    message=f"Interface {name} is administratively shut down.",
                    context={"interface": name}
                )
            )

    # If the user asked for a specific interface but we didn't find it in the output
    if target_interface and not findings:
        findings.append(
            DiagnosticFinding(
                severity=Severity.WARNING,
                message=f"Interface '{target_interface}' was not found in the switch output.",
                context={"target": target_interface}
            )
        )

    return findings