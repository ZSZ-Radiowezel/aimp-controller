import logging
import functools
from typing import Callable, Any

logger = logging.getLogger(__name__)

def log_errors(func: Callable) -> Callable:
    """Decorator to log any errors that occur in the function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            raise
    return wrapper

def handle_exceptions(func: Callable) -> Callable:
    """Decorator to handle exceptions and return None instead of raising."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            return None
    return wrapper

def ensure_connected(func: Callable) -> Callable:
    """Decorator to ensure AIMP client is connected before operation."""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.client:
            self.connect_to_aimp()
        return func(self, *args, **kwargs)
    return wrapper