from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import re
from ..models import WebhookMessage

logger = logging.getLogger(__name__)

class MessageFilter:
    def __init__(self):
        # Configurable filtering parameters
        self.max_message_age_minutes = 5
        self.blocked_keywords = [
            "password",
            "secret",
            "key",
            "token",
            "credential"
        ]
        self.required_fields = ["sender", "content"]
        self.max_content_length = 1000

    def validate_timestamp(self, timestamp: datetime) -> bool:
        """Check if message is not too old."""
        age = datetime.now() - timestamp
        return age <= timedelta(minutes=self.max_message_age_minutes)

    def contains_sensitive_info(self, content: str) -> bool:
        """Check if content contains sensitive information."""
        return any(keyword.lower() in content.lower() for keyword in self.blocked_keywords)

    def sanitize_content(self, content: Any) -> Any:
        """Sanitize content to remove potential sensitive information."""
        if isinstance(content, str):
            # Remove any potential credit card numbers
            content = re.sub(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', '[REDACTED]', content)
            # Remove potential API keys (common formats)
            content = re.sub(r'[a-zA-Z0-9_-]{32,}', '[REDACTED]', content)
        elif isinstance(content, dict):
            return {k: self.sanitize_content(v) for k, v in content.items()}
        elif isinstance(content, list):
            return [self.sanitize_content(item) for item in content]
        return content

    def validate_message_format(self, message: WebhookMessage) -> tuple[bool, Optional[str]]:
        """Validate message format and required fields."""
        try:
            # Check required fields
            for field in self.required_fields:
                if not getattr(message, field):
                    return False, f"Missing required field: {field}"

            # Check content length
            if isinstance(message.content, str) and len(message.content) > self.max_content_length:
                return False, f"Content exceeds maximum length of {self.max_content_length}"

            # Check timestamp
            if not self.validate_timestamp(message.timestamp):
                return False, "Message is too old"

            return True, None
        except Exception as e:
            logger.error(f"Error validating message format: {str(e)}")
            return False, "Invalid message format"

    def filter_message(self, message: WebhookMessage) -> tuple[bool, Optional[str], Optional[WebhookMessage]]:
        """
        Filter and process a message.
        Returns: (is_valid, error_message, processed_message)
        """
        try:
            # Validate message format
            is_valid, error = self.validate_message_format(message)
            if not is_valid:
                return False, error, None

            # Check for sensitive information
            if self.contains_sensitive_info(str(message.content)):
                logger.warning("Message contains sensitive information")
                return False, "Message contains sensitive information", None

            # Sanitize content
            sanitized_message = WebhookMessage(
                sender=message.sender,
                content=self.sanitize_content(message.content),
                timestamp=message.timestamp
            )

            return True, None, sanitized_message

        except Exception as e:
            logger.error(f"Error filtering message: {str(e)}")
            return False, "Error processing message", None
