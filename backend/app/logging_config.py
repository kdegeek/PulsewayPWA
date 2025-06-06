"""
Logging configuration for Pulseway Backend using structlog
"""

import logging
import logging.handlers
import os
from pathlib import Path
import structlog

def setup_logging(log_level: str = "INFO"):
    """Setup application logging with structlog"""

    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Common processors for structlog
    shared_processors = [
        structlog.contextvars.merge_contextvars,  # Adds context variables like request_id
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # This processor prepares event_dict to be passed as kwargs to stdlib logging,
        # making items available as attributes on the LogRecord.
        structlog.stdlib.render_to_log_kwargs,
    ]

    # Configure structlog's global state
    # This is important so that structlog's own internal logs go through the same pipeline
    # if it ever needs to log (e.g., about misconfiguration).
    structlog.configure(
        processors=shared_processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure root logger level using stdlib, as structlog now routes through it
    stdlib_root_logger = logging.getLogger()
    stdlib_root_logger.setLevel(log_level.upper())
    # Clear existing handlers from stdlib root logger to avoid duplicates
    stdlib_root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO) # Set level on handler
    # Added %(request_id)s to the format string. Add default 'None' for logs not part of a request.
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s [%(request_id)s] - %(message)s',
        defaults={"request_id": None}
    )
    console_handler.setFormatter(console_format)
    stdlib_root_logger.addHandler(console_handler)

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "pulseway_backend.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG) # Set level on handler
    # Added %(request_id)s to the format string. Add default 'None' for logs not part of a request.
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s [%(request_id)s] - %(funcName)s:%(lineno)d - %(message)s',
        defaults={"request_id": None}
    )
    file_handler.setFormatter(file_format)
    stdlib_root_logger.addHandler(file_handler)

    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "pulseway_errors.log",
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR) # Set level on handler
    # Re-use file_format for errors, or define a specific one if needed
    error_handler.setFormatter(file_format)
    stdlib_root_logger.addHandler(error_handler)

    # Get a structlog logger instance.
    # The name here is for the logger that setup_logging itself might use.
    # Applications should call structlog.get_logger() in their own modules.
    logger = structlog.get_logger("pulseway_backend.logging_config")
    logger.info("Logging setup complete.", log_level=log_level)

    # The setup_logging function in the original code returned the logger.
    # While structlog encourages getting loggers via structlog.get_logger() directly,
    # returning one here doesn't hurt and maintains a similar interface.
    return logger
