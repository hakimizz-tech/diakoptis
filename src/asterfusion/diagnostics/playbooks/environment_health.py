"""
Environment Health Diagnostic Playbook.
Analyzes Layer 1 hardware sensors: Fans, Power Supplies, and Temperatures.
"""

from typing import List, Dict, Any
from asterfusion.diagnostics.engine import DiagnosticFinding, Severity


def analyze(data: List[Dict[str, Any]], target: str|None = None, **kwargs) -> List[DiagnosticFinding]:
    """
    Analyzes environmental sensor data.
    
    Args:
        data: Parsed list of dictionaries containing COMPONENT, TYPE, VALUE, STATUS.
        target: Optional target (not typically used for global environment).
        
    Returns:
        List of DiagnosticFinding objects.
    """
    findings = []
    
    if not data:
        return findings
        
    # Guard against PARSE_ERRORs injected by the OutputParser
    if "PARSE_ERROR" in data[0]:
        return findings

    # A set of known bad statuses across various switch vendors
    critical_statuses = {"NOT OK", "ABSENT", "ALARM", "CRIT", "FAIL"}

    for row in data:
        component = row.get("COMPONENT", "Unknown")
        comp_type = row.get("TYPE", "Sensor")
        status = str(row.get("STATUS", "")).strip().upper()
        value = str(row.get("VALUE", "")).strip()

        # 1. Check for Hardware Failures (Fans, PSUs)
        if status in critical_statuses:
            findings.append(DiagnosticFinding(
                severity=Severity.CRITICAL,
                message=f"{comp_type} '{component}' is reporting status: {status}",
                context={"action": f"Inspect physical hardware / reseat {component}."}
            ))
            continue  # Skip temperature threshold checks if the sensor is already dead/absent

        # 2. Check Temperature Thresholds
        if comp_type.upper() == "TEMPERATURE":
            try:
                # Strip out 'C', '+', or '°' symbols so we can cast to a float
                # e.g., "+45.0 C" becomes "45.0"
                clean_val = "".join(c for c in value if c.isdigit() or c == ".")
                
                if clean_val:
                    temp_val = float(clean_val)
                    
                    if temp_val > 85.0:
                        findings.append(DiagnosticFinding(
                            severity=Severity.CRITICAL,
                            message=f"{component} temperature is critically high at {temp_val}°C",
                            context={"action": "Verify switch airflow and datacenter cooling immediately."}
                        ))
                    elif temp_val > 75.0:
                        findings.append(DiagnosticFinding(
                            severity=Severity.WARNING,
                            message=f"{component} is running hot at {temp_val}°C",
                            context={"action": "Check ambient temperature and fan operation."}
                        ))
            except ValueError:
                # If the temperature value was completely malformed, silently pass.
                # The user will still see the raw value in the Aggregator table.
                pass

    # 3. Overall Health
    if not findings:
        findings.append(DiagnosticFinding(
            severity=Severity.PASS,
            message="All environmental sensors (Fans, Temps, PSUs) are reporting healthy."
        ))
        
    return findings