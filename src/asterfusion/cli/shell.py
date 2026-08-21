"""
Interactive shell loop using prompt_toolkit.
Handles user input, tab-completion, and command dispatching.
"""

import sys
import shlex
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.patch_stdout import patch_stdout

# Import all the core backend systems 
from asterfusion.config.settings import SETTINGS
from asterfusion.config.inventory import Inventory, InventoryError
from asterfusion.config.command_map import CommandMap, CommandMapError
from asterfusion.resolver.resolver import CommandResolver
from asterfusion.connection.manager import ConnectionManager
from asterfusion.parsing.parser import OutputParser
from asterfusion.diagnostics.engine import DiagnosticsEngine
from asterfusion.rendering.renderer import OutputRenderer
from asterfusion.logging.session_log import audit_logger

# Import the command handlers
from asterfusion.cli.commands import connect, show, check

# Import Diagnostic Playbooks
from asterfusion.diagnostics.playbooks import interface_health, bgp_health


class AsterfusionCLI:
    def __init__(self):
        self.active_host = None 
        
        try:
            # 1. Initialize Configuration Layer
            self.inventory = Inventory(str(SETTINGS.inventory_path))
            self.command_map = CommandMap(str(SETTINGS.command_map_path))
            
            # 2. Initialize Core Engines
            self.resolver = CommandResolver(self.command_map)
            self.conn_manager = ConnectionManager()
            self.parser = OutputParser()
            self.renderer = OutputRenderer()
            
            # 3. Initialize Diagnostics & Register Playbooks
            self.diagnostics = DiagnosticsEngine()
            
            # Register Playbooks for specific mapped commands
            self.diagnostics.register_playbook("check_interface", interface_health.analyze)
            self.diagnostics.register_playbook("check_interfaces", interface_health.analyze)
            self.diagnostics.register_playbook("check_bgp", bgp_health.analyze)
            self.diagnostics.register_playbook("check_bgp_neighbor", bgp_health.analyze)
            
        except (InventoryError, CommandMapError) as e:
            print(f"\n[!] Startup Error: {e}")
            sys.exit(1)

        # 4. Set up dynamic tab-completion
        self.known_commands = ["connect", "disconnect", "exit", "quit", "help", "show", "check"]
        
        # Add all the commands from command_map.yaml for tab-completion 
        # (e.g., 'show_interfaces' becomes 'show interfaces')
        for mapped_cmd in self.command_map.list_commands():
            self.known_commands.append(mapped_cmd.replace("_", " "))
            
        self.completer = WordCompleter(
            self.known_commands, 
            ignore_case=True,
            match_middle=False
        )
        
        # Initialize the prompt_toolkit session
        self.session = PromptSession(completer=self.completer)

    def _get_prompt(self):
        """Generates a dynamic, colored prompt string showing the active host."""
        if self.active_host:
            return HTML(f'<ansicyan>aster-cli</ansicyan> [<ansigreen>{self.active_host}</ansigreen>] > ')
        return HTML('<ansicyan>aster-cli</ansicyan> > ')

    def cmdloop(self) -> int:
        """The main interactive loop. Blocks until the user exits."""
        self.renderer.console.print("[bold cyan]Welcome to the Asterfusion Troubleshooting CLI.[/bold cyan]")
        print("Type 'help' for a list of commands or 'exit' to quit.\n")
        
        audit_logger.info("CLI session started.")

        while True:
            try:
                # patch_stdout ensures background print statements don't break the prompt
                with patch_stdout():
                    user_input = self.session.prompt(self._get_prompt())
                
                # Clean and parse the input
                text = user_input.strip()
                if not text:
                    continue
                
                # Dispatch the command
                should_exit = self.dispatch(text)
                if should_exit:
                    return 0

            except KeyboardInterrupt:
                # User pressed Ctrl+C at the prompt (clears current line)
                continue
            except EOFError:
                # User pressed Ctrl+D
                print("\nExiting...")
                self._shutdown()
                return 0
            except Exception as e:
                print(f"[!] Shell Error: {e}")
                audit_logger.error(f"Unexpected shell error: {e}")

    def dispatch(self, text: str) -> bool:
        """
        Parses the raw input and routes it to the correct handler module.
        Returns True if the CLI should exit, False otherwise.
        """
        try:
            parts = shlex.split(text)
        except ValueError as e:
            print(f"[!] Invalid syntax: {e}")
            return False

        command = parts[0].lower()
        args = parts[1:]

        # --- Built-in Shell Commands ---
        if command in ("exit", "quit"):
            self._shutdown()
            return True
            
        elif command == "help":
            self._handle_help()
            return False
            
        elif command == "connect":
            # Delegate to the standalone connect.py module
            connect.execute(args, self)
            return False
            
        elif command == "disconnect":
            self._handle_disconnect()
            return False

        # --- Operational Commands ---
        elif command == "show":
            # Delegate to the standalone show.py module
            show.execute(args, self)
            return False
            
        elif command == "check":
            # Delegate to the standalone check.py module
            check.execute(args, self)
            return False
            
        else:
            print(f"[!] Unknown command: '{command}'. Type 'help' for available commands.")
            return False

    
    # Internal Shell Helpers
    def _shutdown(self):
        """Safely cleans up connections before exiting."""
        if self.conn_manager.is_connected:
            print(f"Disconnecting from {self.active_host}...")
            self.conn_manager.disconnect()
        audit_logger.info("CLI session ended.")

    def _handle_disconnect(self):
        """Handles manual disconnection from a switch."""
        if not self.conn_manager.is_connected:
            print("[!] Not currently connected to any switch.")
            return
            
        print(f"Disconnected from {self.active_host}.")
        audit_logger.info(f"Manually disconnected from {self.active_host}.")
        
        self.conn_manager.disconnect()
        self.active_host = None

    def _handle_help(self):
        """Dynamically builds a help menu from the command_map.yaml."""
        from rich.table import Table
        
        # Print built-in shell commands
        print("\n--- Built-in Commands ---")
        print("  connect <host>     Connect to a switch in the inventory")
        print("  disconnect         Close the current switch connection")
        print("  exit / quit        Exit the application")
        
        # Build a rich table for mapped commands
        print("\n--- Troubleshooting Commands ---")
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Command", style="cyan bold")
        table.add_column("Description", style="white")
        
        # Iterate through the dynamically loaded CommandMap
        for key, definition in self.command_map.commands.items():
            # Convert 'show_interfaces' to 'show interfaces'
            friendly_name = key.replace("_", " ")
            table.add_row(friendly_name, definition.description)
            
        self.renderer.console.print(table)
        print() # trailing newline