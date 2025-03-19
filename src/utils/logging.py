import logging
from typing import Optional

def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """
    Setup logging configuration.
    
    Args:
        level: Logging level to use
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger('PipelineGenerator')
    logger.setLevel(level)

    # Create console handler with formatting
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)

    return logger
