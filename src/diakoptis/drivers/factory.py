"""
Vendor Driver Factory.
Instantiates the correct SwitchDriver based on the vendor string in the inventory.
"""

from typing import Dict, Any
from diakoptis.drivers.base import SwitchDriver


class UnsupportedVendorError(Exception):
    """Raised when the inventory specifies a vendor we do not have a driver for."""
    pass


def get_driver(hostname: str, host_data: Dict[str, Any], credentials: Dict[str, str]) -> SwitchDriver:
    """
    Factory function to instantiate the correct driver class.
    
    Args:
        hostname: The inventory name of the switch.
        host_data: Dictionary of host attributes (must contain a 'vendor' key).
        credentials: The resolved username, password, and optional secret.
        
    Returns:
        An initialized instance of a class that inherits from SwitchDriver.
        
    Raises:
        UnsupportedVendorError: If the vendor is unknown or missing.
    """
    vendor = host_data.get("vendor", "").lower().strip()
    
    if not vendor:
        raise UnsupportedVendorError(
            f"Host '{hostname}' is missing the required 'vendor' field in inventory.yaml."
        )

    # We use local imports inside the factory function for two reasons:
    # 1. Performance: We only load the heavy Netmiko/Paramiko dependencies for the 
    #    specific vendors we are actively connecting to.
    # 2. Safety: It prevents circular dependency errors during CLI boot up.

    if vendor == "asterfusion":
        from asterfusion.drivers.asterfusion import AsterfusionDriver
        return AsterfusionDriver(hostname, host_data, credentials)
        
    elif vendor == "cisco_ios":
        # Placeholder for future expansion
        # from asterfusion.drivers.cisco_ios import CiscoIOSDriver
        # return CiscoIOSDriver(hostname, host_data, credentials)
        raise UnsupportedVendorError("Cisco IOS support is planned but not yet implemented.")
        
    elif vendor == "huawei_vrp" or vendor == 'huawei':
        from asterfusion.drivers.huawei import HuaweiDriver
        return HuaweiDriver(hostname, host_data, credentials)
        # raise UnsupportedVendorError("Huawei VRP support is planned but not yet implemented.")
        
    else:
        raise UnsupportedVendorError(
            f"Unsupported vendor '{vendor}' for host '{hostname}'. "
            "Please check for typos in your inventory.yaml."
        )