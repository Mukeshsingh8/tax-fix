"""
Simple logging configuration for TaxFix Multi-Agent System.
"""
import logging
import sys
from typing import Optional


def setup_logging(log_level: str = "INFO") -> None:
    """Setup application logging."""
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set specific logger levels
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("langgraph").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


class AgentLogger:
    """Simple logger for agents."""
    
    def __init__(self, agent_name: str, session_id: Optional[str] = None):
        self.logger = logging.getLogger(f"agent.{agent_name}")
        self.agent_name = agent_name
        self.session_id = session_id
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(f"[{self.agent_name}] {message}")
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(f"[{self.agent_name}] {message}")
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(f"[{self.agent_name}] {message}")
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(f"[{self.agent_name}] {message}")
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.logger.critical(f"[{self.agent_name}] {message}")


class PerformanceLogger:
    """Simple performance logger."""
    
    def __init__(self):
        self.logger = logging.getLogger("performance")
    
    def log_agent_execution(self, agent_name: str, execution_time: float, **kwargs):
        """Log agent execution metrics."""
        self.logger.info(f"Agent {agent_name} executed in {execution_time:.3f}s")


# Global performance logger
performance_logger = PerformanceLogger()
