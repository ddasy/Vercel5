from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from datetime import datetime
import json
from mangum import Adapter

from app.models import WebhookMessage
from app.config import get_settings
from app.services.message_filter import MessageFilter
from app.services.okx_api import OKXAPIClient, OKXAPIError
from app.services.response_handler import ResponseHandler
from app.services.error_handler import error_handler, APIError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://vercel5-mocha.vercel.app",
        "http://vercel5-mocha.vercel.app",
        "https://*.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
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
    
    body = await request.body()
    body_str = body.decode('utf-8')
    
    hmac_obj = hmac.new(
        key=settings.WEBHOOK_SECRET.encode('utf-8'),
        msg=body_str.encode('utf-8'),
        digestmod=hashlib.sha1
    )
    
    expected_signature = hmac_obj.hexdigest()
    return hmac.compare_digest(signature, expected_signature)

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/webhook")
async def webhook_handler(request: Request):
    """Handle incoming webhook messages from Vercel."""
    try:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            logger.error("Invalid JSON payload received")
            return JSONResponse(
                status_code=400,
                content={"status": "error", "detail": "Invalid JSON payload"}
            )

        is_valid = await validate_webhook_signature(request)
        if not is_valid:
            logger.warning("Invalid webhook signature")
            return JSONResponse(
                status_code=401,
                content={"status": "error", "detail": "Invalid webhook signature"}
            )
        
        logger.info(f"Received webhook message: {json.dumps(body, indent=2)}")
        
        message = WebhookMessage(
            sender=body.get("sender", "unknown"),
            content=body.get("content"),
            timestamp=datetime.now()
        )
        
        message_filter = MessageFilter()
        is_valid, error_msg, processed_message = message_filter.filter_message(message)
        
        if not is_valid:
            logger.warning(f"Message filtered out: {error_msg}")
            return JSONResponse(
                status_code=400,
                content={"status": "error", "detail": error_msg}
            )
            
        logger.info("Message passed filtering")
        request.state.processed_message = processed_message
        
        response_handler = ResponseHandler()
        start_time = datetime.now().timestamp()
        
        try:
            okx_client = OKXAPIClient()
            response_handler.log_request_details(processed_message, "OKX API")
            result = await okx_client.forward_message(processed_message)
            await okx_client.close()
            
            response_time = datetime.now().timestamp() - start_time
            response_handler.log_response_metrics(response_time, "OKX API")
            
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
            response_time = datetime.now().timestamp() - start_time
            response_handler.log_response_metrics(response_time, "OKX API")
            
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
            response_time = datetime.now().timestamp() - start_time
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

# Create handler for AWS Lambda / Vercel
handler = Adapter(app, lifespan="off")
