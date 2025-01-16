from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

class WebhookMessage(BaseModel):
    sender: str
    content: Any
    timestamp: datetime = datetime.now()
    
class OKXResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error_message: Optional[str] = None
