import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import json
import hmac
import hashlib
import asyncio
import httpx

# Mock response class for API tests
class MockResponse(httpx.Response):
    def __init__(self, status_code: int, json_data: dict):
        super().__init__(status_code, request=httpx.Request("POST", "https://test.com"))
        self._json_data = json_data
    
    def json(self):
        return self._json_data
from app.main import app
from app.models import WebhookMessage
from app.services.message_filter import MessageFilter
from app.services.okx_api import OKXAPIClient, OKXAPIError
from app.services.response_handler import ResponseHandler
from app.services.error_handler import (
    ErrorHandler, WebhookError, ValidationError,
    NetworkError, APIError, SecurityError
)
from app.config import get_settings

client = TestClient(app)

@pytest.fixture
def webhook_signature():
    """Generate valid webhook signature for test requests."""
    def _generate_signature(body: str, secret: str = "test_webhook_secret"):
        return hmac.new(
            secret.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha1
        ).hexdigest()
    return _generate_signature

@pytest.fixture
def valid_message():
    """Create a valid test message."""
    return {
        "sender": "test_sender",
        "content": {
            "instId": "BTC-USDT",
            "side": "buy",
            "sz": "1"
        },
        "timestamp": datetime.now().isoformat()
    }

def test_healthcheck():
    """Test health check endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_webhook_without_signature(valid_message):
    """Test webhook endpoint without signature."""
    response = client.post("/webhook", json=valid_message)
    assert response.status_code == 401
    assert "Invalid webhook signature" in response.json()["detail"]

def test_webhook_with_valid_signature(valid_message, webhook_signature):
    """Test webhook endpoint with valid signature."""
    body = json.dumps(valid_message, separators=(',', ':'))  # Use compact JSON encoding
    signature = webhook_signature(body)
    response = client.post(
        "/webhook",
        json=valid_message,
        headers={"x-vercel-signature": signature}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

@pytest.mark.asyncio
async def test_okx_api_network_failures(monkeypatch, caplog):
    """Test OKX API network failure handling and logging."""
    from app.services.okx_api import OKXAPIClient
    import logging
    caplog.set_level(logging.WARNING)  # Changed to WARNING to capture retry warnings
    
    call_count = 0
    async def mock_request(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:  # Fail twice then succeed
            raise httpx.NetworkError("Connection failed")
        return MockResponse(200, {"code": "0", "data": {"orderId": "12345"}})

    # Create test message
    message = WebhookMessage(
        sender="test",
        content={"instId": "BTC-USDT"},
        timestamp=datetime.now()
    )

    # Patch the request method
    monkeypatch.setattr(httpx.AsyncClient, "request", mock_request)

    # Test retry mechanism and logging
    client = OKXAPIClient()
    result = await client.forward_message(message)
    await client.close()

    # Verify retries and success
    assert call_count == 3
    assert result["data"]["orderId"] == "12345"
    
    # Verify logging of connection failures and retries
    connection_failure_logs = [
        record.message for record in caplog.records
        if "Connection failed" in record.message
    ]
    assert len(connection_failure_logs) >= 2, "Expected at least 2 connection failure logs"
    assert any("retry" in msg.lower() for msg in connection_failure_logs), "Missing retry message"
    assert any("attempt 1/3" in msg for msg in connection_failure_logs), "Missing first attempt log"
    assert any("attempt 2/3" in msg for msg in connection_failure_logs), "Missing second attempt log"

@pytest.mark.asyncio
async def test_okx_api_authentication(monkeypatch, caplog):
    """Test OKX API authentication headers."""
    from app.services.okx_api import OKXAPIClient
    import logging
    caplog.set_level(logging.INFO)
    
    async def mock_request(*args, **kwargs):
        # Verify authentication headers
        headers = kwargs.get("headers", {})
        assert "OK-ACCESS-KEY" in headers
        assert "OK-ACCESS-SIGN" in headers
        assert "OK-ACCESS-TIMESTAMP" in headers
        assert "OK-ACCESS-PASSPHRASE" in headers
        return MockResponse(200, {"code": "0", "data": {"orderId": "12345"}})

    # Create test message
    message = WebhookMessage(
        sender="test",
        content={"instId": "BTC-USDT"},
        timestamp=datetime.now()
    )

    # Patch the request method
    monkeypatch.setattr(httpx.AsyncClient, "request", mock_request)

    # Test API authentication
    client = OKXAPIClient()
    result = await client.forward_message(message)
    await client.close()

    assert result["code"] == "0"

@pytest.mark.asyncio
async def test_okx_api_retry_mechanism(monkeypatch):
    """Test OKX API retry mechanism for network issues."""
    from app.services.okx_api import OKXAPIClient
    import httpx
    
    # Mock httpx client to simulate network errors

    call_count = 0
    async def mock_request(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:  # Fail twice then succeed
            raise httpx.NetworkError("Connection failed")
        return MockResponse(200, {"code": "0", "data": {"orderId": "12345"}})

    # Create test message
    message = WebhookMessage(
        sender="test",
        content={"instId": "BTC-USDT"},
        timestamp=datetime.now()
    )

    # Patch the request method
    monkeypatch.setattr(httpx.AsyncClient, "request", mock_request)

    # Test retry mechanism
    client = OKXAPIClient()
    result = await client.forward_message(message)
    await client.close()

    assert call_count == 3  # Verify it retried twice before succeeding
    assert result["data"]["orderId"] == "12345"

@pytest.mark.asyncio
async def test_okx_api_rate_limit_handling(monkeypatch):
    """Test OKX API rate limit handling."""
    from app.services.okx_api import OKXAPIClient
    import httpx

    call_count = 0
    async def mock_request(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            mock_request = httpx.Request("POST", "https://test.com")
            resp = MockResponse(429, {"code": "1", "msg": "Rate limit exceeded"})
            resp.status_code = 429
            raise httpx.HTTPStatusError("Rate limit", request=mock_request, response=resp)
        return MockResponse(200, {"code": "0", "data": {"orderId": "12345"}})

    # Create test message
    message = WebhookMessage(
        sender="test",
        content={"instId": "BTC-USDT"},
        timestamp=datetime.now()
    )

    # Patch the request method
    monkeypatch.setattr(httpx.AsyncClient, "request", mock_request)

    # Test rate limit handling
    client = OKXAPIClient()
    result = await client.forward_message(message)
    await client.close()

    assert call_count == 2  # Verify it retried after rate limit
    assert result["data"]["orderId"] == "12345"

def test_message_filtering():
    """Test message filtering functionality."""
    filter_service = MessageFilter()
    
    # Test valid message
    valid_msg = WebhookMessage(
        sender="test",
        content={"instId": "BTC-USDT"},
        timestamp=datetime.now()
    )
    is_valid, _, processed = filter_service.filter_message(valid_msg)
    assert is_valid
    assert processed is not None
    
    # Test message with sensitive info
    sensitive_msg = WebhookMessage(
        sender="test",
        content={"password": "secret123"},
        timestamp=datetime.now()
    )
    is_valid, error, _ = filter_service.filter_message(sensitive_msg)
    assert not is_valid
    assert "sensitive information" in error.lower()
    
    # Test old message
    old_msg = WebhookMessage(
        sender="test",
        content={"instId": "BTC-USDT"},
        timestamp=datetime.now() - timedelta(minutes=10)
    )
    is_valid, error, _ = filter_service.filter_message(old_msg)
    assert not is_valid
    assert "too old" in error.lower()

def test_error_handling():
    """Test error handling functionality."""
    handler = ErrorHandler()
    
    # Test API error
    api_error = handler.handle_error(APIError("API timeout"))
    assert api_error.status_code == 502
    
    # Test validation error
    validation_error = handler.handle_error(ValidationError("Invalid format"))
    assert validation_error.status_code == 400
    
    # Test network error
    network_error = handler.handle_error(NetworkError("Connection failed"))
    assert network_error.status_code == 503
    
    # Test security error
    security_error = handler.handle_error(SecurityError("Invalid signature"))
    assert security_error.status_code == 401

def test_response_handling():
    """Test response handling functionality."""
    handler = ResponseHandler()
    message = WebhookMessage(
        sender="test",
        content={"instId": "BTC-USDT"},
        timestamp=datetime.now()
    )
    
    # Test successful response
    success_response = handler.format_response(
        message=message,
        okx_response={"data": {"ordId": "12345"}},
        success=True
    )
    assert success_response["status"] == "success"
    assert "ordId" in success_response["okx_response"]["data"]
    
    # Test error response
    error_response = handler.format_response(
        message=message,
        okx_response=None,
        success=False,
        error="API error"
    )
    assert error_response["status"] == "error"
    assert error_response["processing_result"]["error_message"] == "API error"

def test_response_sanitization():
    """Test response sanitization."""
    handler = ResponseHandler()
    sensitive_response = {
        "data": {
            "apiKey": "secret_key_123",
            "orderId": "12345"
        }
    }
    
    sanitized = handler.sanitize_response(sensitive_response)
    assert sanitized["data"]["apiKey"] == "[REDACTED]"
    assert sanitized["data"]["orderId"] == "12345"

if __name__ == "__main__":
    pytest.main([__file__])
