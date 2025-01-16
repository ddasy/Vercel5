from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import psycopg
import logging
import json
from datetime import datetime
from typing import Dict, Any

from .models import WebhookMessage
from .config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

async def validate_webhook_signature(request: Request) -> bool:
    """Validate the webhook signature from Vercel."""
    import hmac
    import hashlib

    settings = get_settings()
    if not settings.WEBHOOK_SECRET:
        logger.warning("Webhook secret not configured")
        return False
    
    signature = request.headers.get("x-vercel-signature")
    if not signature:
        logger.warning("Missing x-vercel-signature header")
        return False
    
    # Get raw body and convert to string for signature validation
    body = await request.body()
    body_str = body.decode('utf-8')
    
    # Create HMAC SHA1 hash
    hmac_obj = hmac.new(
        key=settings.WEBHOOK_SECRET.encode('utf-8'),
        msg=body_str.encode('utf-8'),
        digestmod=hashlib.sha1
    )
    
    # Compare signatures
    expected_signature = hmac_obj.hexdigest()
    return hmac.compare_digest(signature, expected_signature)

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/webhook")
async def webhook_handler(request: Request):
    """Handle incoming webhook messages from Vercel."""
    try:
        # Parse request body first to avoid signature validation on invalid JSON
        try:
            body = await request.json()
        except json.JSONDecodeError:
            logger.error("Invalid JSON payload received")
            return JSONResponse(
                status_code=400,
                content={"status": "error", "detail": "Invalid JSON payload"}
            )

        # Validate webhook signature
        is_valid = await validate_webhook_signature(request)
        if not is_valid:
            logger.warning("Invalid webhook signature")
            return JSONResponse(
                status_code=401,
                content={"status": "error", "detail": "Invalid webhook signature"}
            )
        
        logger.info(f"Received webhook message: {json.dumps(body, indent=2)}")
        
        # Create WebhookMessage instance for validation
        message = WebhookMessage(
            sender=body.get("sender", "unknown"),
            content=body.get("content"),
            timestamp=datetime.now()
        )
        
        # Filter and validate message
        from .services.message_filter import MessageFilter
        message_filter = MessageFilter()
        is_valid, error_msg, processed_message = message_filter.filter_message(message)
        
        if not is_valid:
            logger.warning(f"Message filtered out: {error_msg}")
            return JSONResponse(
                status_code=400,
                content={"status": "error", "detail": error_msg}
            )
            
        logger.info("Message passed filtering")
        
        # Store processed message for forwarding
        request.state.processed_message = processed_message
        
        # Forward message to OKX API
        from .services.okx_api import OKXAPIClient, OKXAPIError
        from .services.response_handler import ResponseHandler
        from .services.error_handler import error_handler, APIError
        import time
        
        response_handler = ResponseHandler()
        start_time = time.time()
        
        try:
            okx_client = OKXAPIClient()
            
            # Log request details before processing
            response_handler.log_request_details(processed_message, "OKX API")
            
            # Forward message
            result = await okx_client.forward_message(processed_message)
            await okx_client.close()
            
            # Calculate response time and log metrics
            response_time = time.time() - start_time
            response_handler.log_response_metrics(response_time, "OKX API")
            
            # Format and sanitize response
            response = response_handler.format_response(
                message=processed_message,
                okx_response=result,
                success=True
            )
            
            return JSONResponse(
                status_code=200,
                content=response
            )
            
        except OKXAPIError as e:
            response_time = time.time() - start_time
            response_handler.log_response_metrics(response_time, "OKX API")
            
            # Try to recover from API error
            recovery_response = error_handler.recover_from_error(
                APIError(str(e), {"endpoint": "OKX API"})
            )
            
            response = response_handler.format_response(
                message=processed_message,
                okx_response=recovery_response,
                success=bool(recovery_response),
                error=str(e) if not recovery_response else None
            )
            
            if not recovery_response:
                return JSONResponse(
                    status_code=502,
                    content=response
                )
            
            return JSONResponse(
                status_code=200,
                content=response
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            response_handler.log_response_metrics(response_time, "OKX API")
            
            response = response_handler.format_response(
                message=processed_message,
                okx_response=None,
                success=False,
                error=f"Internal error: {str(e)}"
            )
            
            return JSONResponse(
                status_code=500,
                content=response
            )
            
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": "Internal server error"}
        )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions and log them."""
    logger.error(f"HTTP error occurred: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "detail": exc.detail}
    )
