"""
Main entry point for the Asterfusion Troubleshooting CLI.
Can be executed via `aster-cli` or `python -m asterfusion_cli`.
"""
import sys

# This imports the cmd2 application class (which we will build next)
from asterfusion.cli.shell import AsterfusionCLI

def main() -> int:
    """Initialize and run the interactive CLI loop."""
    try:
        # Instantiate the cmd2 shell
        app = AsterfusionCLI()
        
        # Start the interactive prompt. 
        # cmdloop() blocks and handles all user input until they type 'exit' or 'quit'.
        exit_code = app.cmdloop()
        
        return exit_code
        
    except KeyboardInterrupt:
        # Clean exit if the user hits Ctrl+C at the top level
        print("\nExiting Asterfusion CLI. Goodbye!")
        return 0
    except Exception as e:
        # Catch-all for fatal startup errors (e.g., missing YAML configs)
        print(f"\n[!] Fatal Error during startup: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())