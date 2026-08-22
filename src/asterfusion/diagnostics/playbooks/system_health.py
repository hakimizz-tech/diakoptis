"""
System Health Diagnostic Playbook.
Analyzes memory utilization and other system-level metrics.
"""

from typing import List, Dict, Any
from asterfusion.diagnostics.engine import DiagnosticFinding, Severity


def analyze(data: List[Dict[str, Any]], target: str | None = None, **kwargs) -> List[DiagnosticFinding]:
    """
    Analyzes memory utilization data.
    
    Args:
        data: Parsed list of dictionaries containing TOTAL_MEM, USED_MEM, etc.
        target: Optional target (not typically used for global memory).
        
    Returns:
        List of DiagnosticFinding objects.
    """
    findings = []
    
    if not data:
        return findings
        
    # Extract the first row, which contains the main Mem: statistics
    mem_row = data[0]
    
    # Guard against PARSE_ERRORs injected by the OutputParser
    if "PARSE_ERROR" in mem_row:
        return findings
    
    try:
        # Our TextFSM template captured these as string digits, convert to int
        total = int(mem_row.get("TOTAL_MEM", 0))
        used = int(mem_row.get("USED_MEM", 0))
        
        if total > 0:
            utilization = (used / total) * 100
            
            if utilization > 90:
                findings.append(DiagnosticFinding(
                    severity=Severity.CRITICAL,
                    message=f"Memory utilization is critically high at {utilization:.1f}%",
                    context={"action": "Run 'show processes memory' to identify leaking processes."}
                ))
            elif utilization > 75:
                findings.append(DiagnosticFinding(
                    severity=Severity.WARNING,
                    message=f"Memory utilization is elevated at {utilization:.1f}%",
                    context={"action": "Monitor for potential memory leaks."}
                ))
            else:
                findings.append(DiagnosticFinding(
                    severity=Severity.PASS,
                    message=f"Memory utilization is healthy ({utilization:.1f}%)"
                ))
                
    except (ValueError, TypeError):
        # If the data unexpectedly isn't numeric, we silently pass. 
        # The user will still see the raw values in the Aggregator table.
        pass
        
    return findings