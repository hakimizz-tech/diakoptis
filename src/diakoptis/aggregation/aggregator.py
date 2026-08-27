"""
Result Aggregator.
Transforms and merges parsed TextFSM data from multiple switches into 
consolidated views optimized for terminal rendering.
"""

from typing import Dict, List, Any, Optional, Set


class AggregationError(Exception):
    """Raised when data cannot be aggregated (e.g., mismatched schemas)."""
    pass


class ResultAggregator:
    """
    Provides methods to merge parsed data from multiple hosts.
    """

    @staticmethod
    def aggregate_vertical(parsed_results: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Appends the hostname to each row and stacks them vertically into one master list.
        Best for data that doesn't share a common key, like logs or MAC address tables.
        
        Args:
            parsed_results: Dict mapping hostname -> list of parsed dictionaries.
            
        Returns:
            A single list of dictionaries, with a new 'HOST' key at the front.
        """
        master_list = []
        
        for hostname, rows in parsed_results.items():
            if not isinstance(rows, list):
                continue # Skip raw strings or errors
                
            for row in rows:
                # Create a new dict with HOST as the first key for better table rendering
                new_row = {"HOST": hostname}
                new_row.update(row)
                master_list.append(new_row)
                
        return master_list

    @staticmethod
    def aggregate_comparison(
        parsed_results: Dict[str, List[Dict[str, Any]]], 
        primary_key: str, 
        diff_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Pivots the data to compare fields across multiple switches side-by-side.
        
        Example Output row:
        {"INTERFACE": "Ethernet4", "Metric": "OPER_STATUS", "leaf01": "up", "leaf02": "down"}
        
        Args:
            parsed_results: Dict mapping hostname -> list of parsed dictionaries.
            primary_key: The column to group by (e.g., "INTERFACE" or "NEIGHBOR").
            diff_only: If True, only returns rows where the switches disagree.
            
        Returns:
            A list of pivoted dictionaries ready to be drawn as a table.
        """
        # 1. Identify all unique primary keys (e.g., all known interfaces across all switches)
        # and all unique metric fields (e.g., SPEED, MTU, STATUS)
        all_pks: Set[str] = set()
        all_metrics: Set[str] = set()
        
        # Intermediate lookup dictionary: lookup[pk_value][hostname][metric] = value
        lookup: Dict[str, Dict[str, Dict[str, Any]]] = {}
        
        for hostname, rows in parsed_results.items():
            if not isinstance(rows, list):
                continue
                
            for row in rows:
                pk_value = str(row.get(primary_key, "UNKNOWN"))
                all_pks.add(pk_value)
                
                if pk_value not in lookup:
                    lookup[pk_value] = {}
                lookup[pk_value][hostname] = row
                
                # Gather all keys except the primary key itself
                all_metrics.update(k for k in row.keys() if k != primary_key)

        # 2. Build the pivoted rows
        pivoted_rows = []
        hostnames = sorted(list(parsed_results.keys()))
        
        for pk_value in sorted(list(all_pks)):
            for metric in sorted(list(all_metrics)):
                
                # Base row with our identifier and what we are measuring
                row_data = {
                    primary_key: pk_value,
                    "Metric": metric
                }
                
                values_for_this_metric = set()
                
                # Populate the column for each switch
                for host in hostnames:
                    # Default to "-" if a switch is missing this interface/BGP peer entirely
                    val = str(lookup.get(pk_value, {}).get(host, {}).get(metric, "-"))
                    row_data[host] = val
                    values_for_this_metric.add(val)
                
                # 3. Handle 'diff_only' filtering
                # If diff_only is True, we only append the row if there is more than 1 unique value
                # (meaning the switches are not in identical states).
                if diff_only:
                    # Ignore rows where everyone is "-" (missing)
                    if len(values_for_this_metric) > 1:
                        pivoted_rows.append(row_data)
                else:
                    pivoted_rows.append(row_data)
                    
        return pivoted_rows