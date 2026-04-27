"""
Logging configuration for the Mental Burnout System
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Create logs directory
log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

# Configure logging
log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# File handler
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# Dictionary to store logger instances
_loggers = {}

def setup_logger(name: str, log_level: Optional[str] = None) -> logging.Logger:
    """
    Setup a logger with the given name.
    
    Args:
        name: Name of the logger (usually __name__)
        log_level: Optional log level (DEBUG, INFO, WARNING, ERROR)
        
    Returns:
        Configured logger instance
    """
    global _loggers
    
    # Return existing logger if already created
    if name in _loggers:
        return _loggers[name]
    
    # Create new logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers
    logger.handlers.clear()
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Set custom log level if provided
    if log_level:
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        if log_level.upper() in level_map:
            logger.setLevel(level_map[log_level.upper()])
    
    # Store in cache
    _loggers[name] = logger
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get an existing logger or create a new one.
    
    Args:
        name: Name of the logger
        
    Returns:
        Logger instance
    """
    if name in _loggers:
        return _loggers[name]
    return setup_logger(name)


def set_log_level(level: str) -> None:
    """
    Set log level for all loggers.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    if level.upper() not in level_map:
        raise ValueError(f"Invalid log level: {level}")
    
    numeric_level = level_map[level.upper()]
    
    # Update all existing loggers
    for logger in _loggers.values():
        logger.setLevel(numeric_level)
    
    # Update handlers
    console_handler.setLevel(numeric_level)
    
    logging.getLogger().setLevel(numeric_level)
    
    print(f"✅ Log level set to: {level.upper()}")


def get_log_file_path() -> Path:
    """
    Get the current log file path.
    
    Returns:
        Path to the current log file
    """
    return log_file


def clear_log_file() -> None:
    """Clear the current log file."""
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"Log cleared at {datetime.now()}\n")
        print(f"✅ Log file cleared: {log_file}")
    except Exception as e:
        print(f"❌ Failed to clear log file: {e}")


class LoggerMixin:
    """
    Mixin class to add logging capability to any class.
    """
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        if not hasattr(self, '_logger'):
            self._logger = setup_logger(self.__class__.__name__)
        return self._logger
    
    def log_debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)
    
    def log_info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)
    
    def log_warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)
    
    def log_error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)
    
    def log_critical(self, message: str) -> None:
        """Log critical message."""
        self.logger.critical(message)


# Create default logger for the module
logger = setup_logger(__name__)

if __name__ == "__main__":
    print("="*50)
    print("📝 Testing Logger Module")
    print("="*50)
    
    # Test basic logging
    test_logger = setup_logger("test_logger")
    print(f"\n📊 Log file: {get_log_file_path()}")
    
    print("\n📝 Writing test messages...")
    test_logger.debug("This is a DEBUG message")
    test_logger.info("This is an INFO message") 
    test_logger.warning("This is a WARNING message")
    test_logger.error("This is an ERROR message")
    
    print("\n✅ Check the log file for messages")
    
    # Test LoggerMixin
    print("\n🧪 Testing LoggerMixin...")
    
    class TestClass(LoggerMixin):
        def test_method(self):
            self.log_info("This is a test info message")
            self.log_debug("This is a test debug message")
    
    test_obj = TestClass()
    test_obj.test_method()
    
    # Test set_log_level
    print("\n🎚️ Testing log level change...")
    set_log_level("WARNING")
    test_logger.info("This INFO should NOT appear (level is WARNING)")
    test_logger.warning("This WARNING should appear")
    
    # Reset log level
    set_log_level("INFO")
    
    print("\n" + "="*50)
    print("✅ Logger test completed successfully!")
    print("="*50)