"""
Decorator-based registry for diagnostics playbooks.
"""

from typing import Callable, Dict


PLAYBOOK_REGISTRY: Dict[str, Callable] = {}


def playbook(*command_keys: str) -> Callable:
    """Registers a playbook function for one or more command keys."""

    def decorator(func: Callable) -> Callable:
        for command_key in command_keys:
            PLAYBOOK_REGISTRY[command_key] = func
        return func

    return decorator
