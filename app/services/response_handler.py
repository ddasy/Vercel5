from typing import Dict, Any, Optional
import logging
from datetime import datetime
from ..models import WebhookMessage

logger = logging.getLogger(__name__)

class ResponseHandler:
    def __init__(self):
        self.sensitive_fields = [
            "key", "secret", "password", "token", "credential",
            "apiKey", "secretKey", "passphrase"
        ]

    def sanitize_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive information from response."""
        sanitized = {}
        for key, value in response.items():
            if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_response(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self.sanitize_response(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized

    def format_response(
        self,
        message: Optional[WebhookMessage],
        okx_response: Optional[Dict[str, Any]],
        success: bool,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Format response for logging and client feedback."""
        current_time = datetime.now().isoformat()
        response = {
            "timestamp": current_time,
            "request_id": str(hash(f"{current_time}")),
            "status": "success" if success else "error",
            "sender": message.sender if message else "unknown",
            "processing_result": {
                "success": success,
                "error_message": error if error else None,
            },
            "okx_response": self.sanitize_response(okx_response) if okx_response else None
        }
        
        # Log the response
        log_level = logging.INFO if success else logging.ERROR
        logger.log(
            log_level,
            f"Message processing completed - "
            f"Status: {response['status']}, "
            f"Sender: {response['sender']}, "
            f"Request ID: {response['request_id']}"
        )
        
        if error:
            logger.error(f"Error details - Request ID: {response['request_id']}, Error: {error}")
        
        return response

    def log_request_details(self, message: Optional[WebhookMessage], endpoint: str) -> None:
        """Log details about the request being processed."""
        if not message:
            logger.warning("Attempted to log details for None message")
            return
            
        logger.info(
            f"Processing request - "
            f"Sender: {message.sender}, "
            f"Timestamp: {message.timestamp.isoformat()}, "
            f"Endpoint: {endpoint}"
        )

    def log_response_metrics(self, response_time: float, endpoint: str) -> None:
        """Log performance metrics."""
        logger.info(
            f"Response metrics - "
            f"Endpoint: {endpoint}, "
            f"Response time: {response_time:.3f}s"
        )
