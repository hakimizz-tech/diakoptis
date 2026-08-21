"""
Connection exceptions module.
Provides clean, application-level exceptions to wrap raw Netmiko errors,
so the rest of the CLI doesn't need to depend directly on Netmiko.
"""

class SwitchConnectionError(Exception):
    """
    Base exception for all switch connection issues.
    Catching this will catch any connection-related error in the CLI.
    """
    pass


class SwitchAuthError(SwitchConnectionError):
    """
    Raised when SSH authentication fails (invalid username, password, or keys).
    Wraps netmiko.exceptions.NetmikoAuthenticationException.
    """
    pass


class SwitchTimeoutError(SwitchConnectionError):
    """
    Raised when the switch is unreachable, or the connection times out.
    Wraps netmiko.exceptions.NetmikoTimeoutException.
    """
    pass


class SwitchCommandExecutionError(SwitchConnectionError):
    """
    Raised when a specific command fails to execute on the switch
    (e.g., privilege level too low, or unexpected CLI prompt change).
    """
    pass