"""
System Health Universal Diagnostic Playbook.
Analyzes CPU, Memory, and Disk utilization across any vendor.
"""

from typing import List, Dict, Any
from asterfusion.diagnostics.engine import DiagnosticFinding, Severity
from asterfusion.diagnostics.playbooks.registry import playbook

@playbook("check_cpu", "check_memory", "check_disk")
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
    
    if not data or "PARSE_ERROR" in data[0]:
        return findings
        
    row = data[0]
    
    # 1. Check CPU
    if "CPU_PCT" in row:
        try:
            cpu = float(row["CPU_PCT"])
            if cpu > 85.0:
                findings.append(DiagnosticFinding(Severity.CRITICAL, f"CPU utilization critical at {cpu}%", {"action": "Check active processes."}))
            elif cpu > 70.0:
                findings.append(DiagnosticFinding(Severity.WARNING, f"CPU utilization elevated at {cpu}%"))
        except ValueError:
            pass

    # 2. Check Memory (Prefer direct percentage, fallback to math calculation)
    try:
        mem_pct = None
        if "MEM_PCT" in row:
            mem_pct = float(row["MEM_PCT"])
        elif "TOTAL_MEM_BYTES" in row and "USED_MEM_BYTES" in row:
            total = int(row["TOTAL_MEM_BYTES"])
            used = int(row["USED_MEM_BYTES"])
            if total > 0:
                mem_pct = (used / total) * 100

        if mem_pct is not None:
            if mem_pct > 90.0:
                findings.append(DiagnosticFinding(Severity.CRITICAL, f"Memory utilization critical at {mem_pct:.1f}%"))
            elif mem_pct > 75.0:
                findings.append(DiagnosticFinding(Severity.WARNING, f"Memory utilization elevated at {mem_pct:.1f}%"))
    except ValueError:
        pass

    # 3. Check Disk
    if "DISK_PCT" in row:
        try:
            disk = float(row["DISK_PCT"])
            if disk > 90.0:
                findings.append(DiagnosticFinding(Severity.CRITICAL, f"Disk space critical at {disk}%", {"action": "Clear old logs or image files."}))
            elif disk > 80.0:
                findings.append(DiagnosticFinding(Severity.WARNING, f"Disk space elevated at {disk}%"))
        except ValueError:
            pass

    # Global Health Fallback
    if not findings:
        findings.append(DiagnosticFinding(Severity.PASS, "System resources (CPU/Mem/Disk) are healthy."))
        
    return findings