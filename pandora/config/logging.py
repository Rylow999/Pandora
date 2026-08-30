"""
Logging configuration for Pandora.
Centralized logging setup with consistent formatting.
"""

import logging
import sys
from pathlib import Path


def setup_logging(level: int = logging.INFO, log_file: str | None = None) -> logging.Logger:
    """
    Configura logging centralizado para Pandora.
    
    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
        log_file: Archivo opcional para log persistente
        
    Returns:
        Logger configurado
    """
    logger = logging.getLogger("pandora")
    logger.setLevel(level)
    
    # Evitar duplicados si ya configurado
    if logger.handlers:
        return logger
    
    # Formato consistente
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler opcional
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "pandora") -> logging.Logger:
    """Obtiene logger hijo para un módulo específico."""
    return logging.getLogger(f"pandora.{name}")


# Logger por defecto
default_logger = setup_logging()


if __name__ == "__main__":
    # Test
    logger = get_logger("test")
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")