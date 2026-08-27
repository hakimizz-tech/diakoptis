"""
Session Log and Audit module.
Provides a centralized logger to record user actions, command executions, 
and application errors independently of the raw Netmiko SSH logs.
"""

import logging
import getpass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from diakoptis.config.settings import SETTINGS

AUDIT_LOGGER_NAME = "asterfusion_audit"


class ContextFilter(logging.Filter):
    """
    Injects the local operating system username into every log record.
    This ensures the audit trail records *who* executed the commands.
    """
    def filter(self, record):
        try:
            record.username = getpass.getuser()
        except Exception:
            record.username = "unknown_user"
        return True


def _setup_audit_logger() -> logging.Logger:
    """
    Configures and returns the global audit logger.
    Uses a RotatingFileHandler to keep log sizes manageable.
    """
    logger = logging.getLogger(AUDIT_LOGGER_NAME)

    # If the logger is already configured (e.g., on reload), don't add duplicate handlers
    if logger.handlers:
        return logger

    # Resolve log level from settings (e.g., INFO, DEBUG)
    log_level = getattr(logging, SETTINGS.log_level.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Ensure log directory exists
    SETTINGS.log_dir.mkdir(parents=True, exist_ok=True)
    audit_log_path = SETTINGS.log_dir / "aster_cli_audit.log"

    # Setup file handler: 5 MB max per file, keep 5 rotating backups
    file_handler = RotatingFileHandler(
        audit_log_path, 
        maxBytes=5 * 1024 * 1024, 
        backupCount=5
    )

    # Format: [2026-08-21 14:30:00] [INFO] [user123] Executed 'check_bgp' on lab-leaf01
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(username)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addFilter(ContextFilter())

    # Note: We purposely do NOT add a StreamHandler (console output) here.
    # The 'rich' OutputRenderer handles all console formatting for the user.
    # This logger is strictly for background file auditing.

    return logger


# Expose a pre-configured, singleton logger instance for the application to import
audit_logger = _setup_audit_logger()