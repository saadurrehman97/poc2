"""
Centralized logging configuration for Neptune Plumbing Pipeline
"""
import logging
import sys
import os
from pathlib import Path
import warnings

# Suppress all warnings
warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow warnings
os.environ['CUDA_VISIBLE_DEVICES'] = '0'

# Suppress ONNX runtime warnings at logger level
logging.getLogger("onnxruntime").setLevel(logging.ERROR)
logging.getLogger("onnxruntime.transformers").setLevel(logging.ERROR)

# Create logs directory
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Log file path
LOG_FILE = LOGS_DIR / "neptune.log"


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )
        
        # File handler (detailed)
        file_handler = logging.FileHandler(LOG_FILE)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
        
        # Console handler (less detailed)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    return logger


def log_section(logger: logging.Logger, title: str, char: str = "="):
    """
    Log a formatted section header
    
    Args:
        logger: Logger instance
        title: Section title
        char: Character to use for border
    """
    border = char * 60
    logger.info(border)
    logger.info(title)
    logger.info(border)


def log_step(logger: logging.Logger, step: str, substep: str = ""):
    """
    Log a processing step
    
    Args:
        logger: Logger instance
        step: Main step description
        substep: Optional substep description
    """
    if substep:
        logger.info(f"   {substep}")
    else:
        logger.info(f"→ {step}")
