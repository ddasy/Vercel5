from typing import Dict, Any, Optional
import httpx
import hmac
import base64
import json
import logging
import asyncio
from datetime import datetime, timezone
import time
from ..config import get_settings
from ..models import WebhookMessage

logger = logging.getLogger(__name__)

class OKXAPIError(Exception):
    """Custom exception for OKX API errors."""
    pass

class OKXAPIClient:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.OKX_API_URL
        self.api_key = self.settings.OKX_API_KEY
        self.secret_key = self.settings.OKX_SECRET_KEY
        self.passphrase = self.settings.OKX_PASSPHRASE
        
        if not all([self.api_key, self.secret_key, self.passphrase]):
            raise ValueError("OKX API credentials not properly configured")
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0
        )

    def _generate_timestamp(self) -> str:
        """Generate ISO timestamp in UTC."""
        return datetime.now(timezone.utc).isoformat()[:-9] + 'Z'

    def _sign_request(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        """Generate the signature for the request."""
        message = timestamp + method.upper() + request_path + body
        mac = hmac.new(
            bytes(self.secret_key, 'utf-8'),
            bytes(message, 'utf-8'),
            digestmod='sha256'
        )
        return base64.b64encode(mac.digest()).decode('utf-8')

    def _get_headers(self, method: str, request_path: str, body: str = "") -> Dict[str, str]:
        """Generate headers for OKX API request."""
        timestamp = self._generate_timestamp()
        sign = self._sign_request(timestamp, method, request_path, body)
        
        return {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": sign,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json"
        }

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Dict[str, Any]:
        """Make request to OKX API with retry mechanism."""
        request_path = f"/api/v5/{endpoint}"
        body = json.dumps(data) if data else ""
        headers = self._get_headers(method, request_path, body)
        
        for attempt in range(max_retries):
            try:
                response = await self.client.request(
                    method=method,
                    url=request_path,
                    headers=headers,
                    json=data if data else None
                )
                
                response.raise_for_status()
                result = response.json()
                
                if result.get("code") == "0":
                    return result
                else:
                    raise OKXAPIError(f"OKX API Error: {result.get('msg', 'Unknown error')}")
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit
                    if attempt < max_retries - 1:
                        logger.warning(f"Rate limit hit (attempt {attempt + 1}/{max_retries}): {str(e)}")
                        await asyncio.sleep(retry_delay * (2 ** attempt))
                        continue
                logger.error(f"HTTP error occurred: {str(e)}")
                raise OKXAPIError(f"HTTP error: {str(e)}")
                
            except httpx.NetworkError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Connection failed, will retry (attempt {attempt + 1}/{max_retries}): {str(e)}")
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
                logger.error(f"Network error after {max_retries} attempts: {str(e)}")
                raise OKXAPIError(f"Network error: {str(e)}")
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Request failed, will retry (attempt {attempt + 1}/{max_retries}): {str(e)}")
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
                logger.error(f"Error making request to OKX API: {str(e)}")
                raise OKXAPIError(f"Request failed: {str(e)}")
        
        raise OKXAPIError("Max retries exceeded")

    def _determine_endpoint(self, content: Any) -> tuple[str, Dict[str, Any]]:
        """Determine appropriate OKX API endpoint and format data based on message content."""
        if isinstance(content, dict):
            # If content has specific trading instructions
            if all(key in content for key in ["instId", "side", "sz"]):
                return "trade/order", content
            # If content has market data request
            elif "instId" in content and content.get("type") == "market_data":
                return "market/ticker", {"instId": content["instId"]}
        
        # Default to a safe, read-only endpoint
        return "market/tickers", {"instId": "BTC-USDT"}

    async def forward_message(self, message: Optional[WebhookMessage]) -> Dict[str, Any]:
        """Forward processed message to appropriate OKX API endpoint."""
        try:
            if not message:
                raise OKXAPIError("Message cannot be None")

            # Determine endpoint and format data based on message content
            endpoint, base_data = self._determine_endpoint(message.content)
            
            # Add metadata
            data = {
                **base_data,
                "timestamp": message.timestamp.isoformat(),
                "source": message.sender
            }
            
            logger.info(f"Forwarding message to OKX API endpoint: {endpoint}")
            return await self._make_request("POST", endpoint, data)
            
        except Exception as e:
            logger.error(f"Error forwarding message to OKX API: {str(e)}")
            raise OKXAPIError(f"Failed to forward message: {str(e)}")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
