"""
Interactive shell loop using prompt_toolkit (v2 Architecture).
Handles user input, tab-completion, multi-switch targeting, and command dispatching.
"""

import sys
import shlex
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.patch_stdout import patch_stdout

# Import all the core backend systems 
from diakoptis.config.settings import SETTINGS
from diakoptis.config.inventory import Inventory, InventoryError
from diakoptis.config.command_map import CommandMap, CommandMapError
from diakoptis.config.credentials import CredentialManager
from diakoptis.targeting.target_parser import TargetParser

from diakoptis.resolver.resolver import CommandResolver
from diakoptis.connection.pool import SessionPool
from diakoptis.parsing.parser import OutputParser
from diakoptis.diagnostics.engine import DiagnosticsEngine
from diakoptis.aggregation.aggregator import ResultAggregator
from diakoptis.rendering.renderer import OutputRenderer
from diakoptis.logging.session_log import audit_logger

#  Import the command handlers 
from diakoptis.cli.commands import connect, show, check

# Import Diagnostic Playbooks
from diakoptis.diagnostics.playbooks import register_playbooks



class DiakoptisCLI:
    def __init__(self):
        try:
            # 1. Initialize Configuration & Data Layer
            self.inventory = Inventory(str(SETTINGS.inventory_path))
            self.command_map = CommandMap(str(SETTINGS.command_map_path))
            self.cred_manager = CredentialManager(self.inventory)
            self.target_parser = TargetParser(self.inventory)
            
            # 2. Initialize Core Engines (v2 Multi-Switch Capable)
            self.resolver = CommandResolver(self.command_map)
            self.pool = SessionPool(max_workers=SETTINGS.max_concurrent_sessions)
            
            self.aggregator = ResultAggregator()
            self.renderer = OutputRenderer()

            self.parser = OutputParser(templates_root=str(SETTINGS.templates_root))
            
            # 3. Initialize Diagnostics & Register Playbooks
            self.diagnostics = DiagnosticsEngine()
            register_playbooks(self.diagnostics)
            
            
        except (InventoryError, CommandMapError) as e:
            print(f"\n[!] Startup Error: {e}")
            sys.exit(1)

        # 4. Set up dynamic tab-completion
        self.known_commands = ["connect", "disconnect", "exit", "quit", "help", "show", "check"]
        
        for mapped_cmd in self.command_map.list_commands():
            self.known_commands.append(mapped_cmd.replace("_", " "))
            
        self.completer = WordCompleter(
            self.known_commands, 
            ignore_case=True,
            match_middle=False
        )
        
        self.session = PromptSession(completer=self.completer)

    def _get_prompt(self):
        """Generates a dynamic, colored prompt string showing active hosts."""
        if self.pool.has_active_sessions:
            hosts = self.pool.active_hostnames
            # If 1 or 2 hosts, list them. If more, show a count (e.g., "5 hosts")
            if len(hosts) <= 2:
                host_str = ",".join(hosts)
            else:
                host_str = f"{len(hosts)} hosts"
            return HTML(f'<ansicyan>diakoptis-cli</ansicyan> [<ansigreen>{host_str}</ansigreen>] > ')
            
        return HTML('<ansicyan>diakoptis-cli</ansicyan> > ')

    def cmdloop(self) -> int:
        """The main interactive loop. Blocks until the user exits."""
        self.renderer.console.print("[bold cyan]Welcome to the diakoptis Troubleshooting CLI (v2).[/bold cyan]")
        print("Type 'help' for a list of commands or 'exit' to quit.\n")
        
        audit_logger.info("CLI session started.")

        while True:
            try:
                with patch_stdout():
                    user_input = self.session.prompt(self._get_prompt())
                
                text = user_input.strip()
                if not text:
                    continue
                
                should_exit = self.dispatch(text)
                if should_exit:
                    return 0

            except KeyboardInterrupt:
                continue
            except EOFError:
                print("\nExiting...")
                self._shutdown()
                return 0
            except Exception as e:
                print(f"[!] Shell Error: {e}")
                audit_logger.error(f"Unexpected shell error: {e}")

    def dispatch(self, text: str) -> bool:
        """Parses the raw input and routes it to the correct handler module."""
        try:
            parts = shlex.split(text)
        except ValueError as e:
            print(f"[!] Invalid syntax: {e}")
            return False

        command = parts[0].lower()
        args = parts[1:]

        # Built-in Shell Commands
        if command in ("exit", "quit"):
            self._shutdown()
            return True
            
        elif command == "help":
            self._handle_help()
            return False
            
        elif command == "connect":
            connect.execute(args, self)
            return False
            
        elif command == "disconnect":
            self._handle_disconnect()
            return False

        # Operational Commands 
        elif command == "show":
            show.execute(args, self)
            return False
            
        elif command == "check":
            check.execute(args, self)
            return False
            
        else:
            print(f"[!] Unknown command: '{command}'. Type 'help' for available commands.")
            return False

    # Internal Shell Helpers
    def _shutdown(self):
        """Safely cleans up connections before exiting."""
        if self.pool.has_active_sessions:
            print("Disconnecting from all switches...")
            self.pool.disconnect_all()
        audit_logger.info("CLI session ended.")

    def _handle_disconnect(self):
        """Handles manual disconnection from all switches."""
        if not self.pool.has_active_sessions:
            print("[!] Not currently connected to any switch.")
            return
            
        print("Disconnecting from all active sessions...")
        self.pool.disconnect_all()
        audit_logger.info("Manually disconnected from all switches.")

    def _handle_help(self):
        """Dynamically builds a help menu from the command_map.yaml."""
        from rich.table import Table
        
        print("\n--- Built-in Commands ---")
        print("  connect <expr>     Connect to switches (e.g., 'leaf01,leaf02' or '@role:leaf')")
        print("  disconnect         Close all current switch connections")
        print("  exit / quit        Exit the application")
        
        print("\n--- Troubleshooting Commands ---")
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Command", style="cyan bold")
        table.add_column("Description", style="white")
        
        for key, definition in self.command_map.commands.items():
            friendly_name = key.replace("_", " ")
            table.add_row(friendly_name, definition.description)
            
        self.renderer.console.print(table)
        print()