from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import json
from datetime import datetime

from .models import WebhookMessage
from .config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)
logger.propagate = True

app = FastAPI()

# Disable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    """Health check endpoint"""
    return {"status": "ok"}

@app.post("/webhook")
async def webhook_handler(request: Request):
    """Handle incoming webhook messages."""
    try:
        # Parse request body
        try:
            body = await request.json()
        except json.JSONDecodeError:
            logger.error("Invalid JSON payload received")
            return JSONResponse(
                status_code=400,
                content={"status": "error", "detail": "Invalid JSON payload"}
            )

        # Log the received webhook
        logger.info(f"Received webhook message: {json.dumps(body, indent=2)}")

        # Create response
        response = {
            "status": "success",
            "message": "Webhook received successfully",
            "timestamp": datetime.now().isoformat(),
            "data": body
        }

        return JSONResponse(
            status_code=200,
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
