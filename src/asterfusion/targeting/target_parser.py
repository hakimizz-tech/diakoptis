"""
Target Expression Parser.
Translates user targeting strings ("switch1,switch2" or "@site:nairobi&@role:leaf")
into a concrete list of inventory hostnames using set algebra.
"""

from typing import List, Set


class TargetParseError(Exception):
    """Raised when a target expression is invalid or matches no hosts."""
    pass


class TargetParser:
    def __init__(self, inventory):
        """
        Initializes the parser with the loaded Inventory object.
        
        Args:
            inventory: The Inventory instance (provides list_hosts(), get_host(), get_group()).
        """
        self.inventory = inventory

    def parse(self, expression: str) -> List[str]:
        """
        Parses a full expression into a deduplicated, sorted list of hostnames.
        Example: "switch1, @core_uplinks, @site:nairobi&@role:leaf"
        
        Args:
            expression: The raw string provided by the user.
            
        Returns:
            A list of valid hostnames.
            
        Raises:
            TargetParseError: If syntax is invalid, a host is missing, or the result is empty.
        """
        if not expression or not expression.strip():
            raise TargetParseError("Target expression cannot be empty.")

        # Split by comma to handle the Union (OR) of multiple targets e.g switch1,switch2 
        tokens = [t.strip() for t in expression.split(",")]
        final_hosts: Set[str] = set()

        for token in tokens:
            if not token:
                continue
            
            # Resolve the token (which might be a single host or an intersection)
            resolved_subset = self._resolve_token(token)
            
            # Add to our final aggregate set (Union)
            final_hosts.update(resolved_subset)

        if not final_hosts:
            raise TargetParseError(f"Expression '{expression}' matched no hosts in the inventory.")

        return sorted(list(final_hosts))

    def _resolve_token(self, token: str) -> Set[str]:
        """
        Resolves a single token, handling intersections (&) if present.
        """
        # 2. Handle Intersection (AND)
        if "&" in token:
            sub_tokens = [t.strip() for t in token.split("&")]
            
            # Initialize the intersected set with the results of the first sub-token
            intersected_hosts = self._resolve_single_filter(sub_tokens[0])
            
            # Intersect with the remaining sub-tokens
            for sub in sub_tokens[1:]:
                next_subset = self._resolve_single_filter(sub)
                intersected_hosts = intersected_hosts.intersection(next_subset)
                
            return intersected_hosts
            
        # 3. Handle a standard, single token
        return self._resolve_single_filter(token)

    def _resolve_single_filter(self, query: str) -> Set[str]:
        """
        Resolves a base filter: explicit hostname, @group, or @attribute:value.
        """
        # A. Explicit Hostname (e.g., 'lab-leaf01') 
        if not query.startswith("@"):
            if query not in self.inventory.list_hosts():
                raise TargetParseError(f"Host '{query}' not found in inventory.")
            return {query}

        filter_expr = query[1:]  # Strip the '@'

        # B. Attribute Filter (e.g., '@site:nairobi')
        if ":" in filter_expr:
            attr_name, attr_value = filter_expr.split(":", 1)
            return self._get_hosts_by_attribute(attr_name, attr_value)
            
        # C. Curated Group Filter (e.g., '@core_uplinks')
        return self._get_hosts_by_group(filter_expr)

    def _get_hosts_by_attribute(self, attr_name: str, target_value: str) -> Set[str]:
        """Finds all hosts where host_data[attr_name] == target_value."""
        matched = set()
        
        for hostname in self.inventory.list_hosts():
            host_data = self.inventory.get_host(hostname)
            
            # Case-insensitive comparison for friendliness
            actual_value = str(host_data.get(attr_name, "")).lower()
            if actual_value == target_value.lower():
                matched.add(hostname)
                
        return matched

    def _get_hosts_by_group(self, group_name: str) -> Set[str]:
        """Finds all hosts listed in a curated group block in the inventory."""
        group_hosts = self.inventory.get_group(group_name)
        if group_hosts is None:
            raise TargetParseError(f"Group '@{group_name}' is not defined in inventory.yaml.")
            
        # Validate that the hosts inside the group actually exist
        valid_hosts = set()
        for host in group_hosts:
            if host not in self.inventory.list_hosts():
                raise TargetParseError(
                    f"Group '@{group_name}' contains host '{host}', which is not in the inventory."
                )
            valid_hosts.add(host)
            
        return valid_hosts