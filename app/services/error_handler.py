from typing import Dict, Any, Optional, Type
import logging
import traceback
from datetime import datetime
import json
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class WebhookError(Exception):
    """Base exception for webhook processing errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()
        self._log_error()

    def _log_error(self):
        """Log error with details and stack trace."""
        error_data = {
            "timestamp": self.timestamp.isoformat(),
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "stack_trace": traceback.format_exc()
        }
        logger.error(f"Error occurred: {json.dumps(error_data, indent=2)}")

class ValidationError(WebhookError):
    """Raised when message validation fails."""
    pass

class NetworkError(WebhookError):
    """Raised when network-related issues occur."""
    pass

class APIError(WebhookError):
    """Raised when API calls fail."""
    pass

class SecurityError(WebhookError):
    """Raised when security checks fail."""
    pass

class ErrorHandler:
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.error_threshold = 5  # Number of errors before triggering alerts

    def _increment_error_count(self, error_type: str):
        """Track error occurrences for monitoring."""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        if self.error_counts[error_type] >= self.error_threshold:
            self._alert_error_threshold(error_type)
            self.error_counts[error_type] = 0

    def _alert_error_threshold(self, error_type: str):
        """Log alert when error threshold is reached."""
        logger.critical(
            f"Error threshold reached for {error_type}. "
            f"Occurred {self.error_threshold} times."
        )

    def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> HTTPException:
        """Handle different types of errors and return appropriate HTTP response."""
        context = context or {}
        error_mapping = {
            ValidationError: (400, "Invalid request"),
            NetworkError: (503, "Service temporarily unavailable"),
            APIError: (502, "API error"),
            SecurityError: (401, "Security check failed"),
        }

        for error_type, (status_code, default_message) in error_mapping.items():
            if isinstance(error, error_type):
                self._increment_error_count(error_type.__name__)
                return HTTPException(
                    status_code=status_code,
                    detail={
                        "error": error_type.__name__,
                        "message": str(error),
                        "timestamp": datetime.now().isoformat(),
                        "context": context
                    }
                )

        # Handle unexpected errors
        logger.error(f"Unexpected error: {str(error)}\nContext: {context}")
        return HTTPException(
            status_code=500,
            detail={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "timestamp": datetime.now().isoformat()
            }
        )

    def recover_from_error(self, error: Exception) -> Optional[Dict[str, Any]]:
        """Attempt to recover from certain types of errors."""
        if isinstance(error, NetworkError):
            # Return cached response if available
            return {"status": "cached", "message": "Using cached response"}
        elif isinstance(error, APIError):
            # Return fallback response
            return {"status": "fallback", "message": "Using fallback response"}
        return None

error_handler = ErrorHandler()  # Singleton instance
