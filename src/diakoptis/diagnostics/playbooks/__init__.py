"""
Diagnostics playbook package exports and registration helpers.
"""

from diakoptis.diagnostics.playbooks.registry import PLAYBOOK_REGISTRY

# Import modules so decorators execute and populate PLAYBOOK_REGISTRY.
from diakoptis.diagnostics.playbooks import bgp_neighbor_detail  # noqa: F401
from diakoptis.diagnostics.playbooks import bgp_health  # noqa: F401
from diakoptis.diagnostics.playbooks import environment_health  # noqa: F401
from diakoptis.diagnostics.playbooks import interface_health  # noqa: F401
from diakoptis.diagnostics.playbooks import system_health  # noqa: F401


def register_playbooks(engine) -> None:
    """Registers all discovered playbooks into a DiagnosticsEngine instance."""
    for command_key, playbook_func in PLAYBOOK_REGISTRY.items():
        engine.register_playbook(command_key, playbook_func)
