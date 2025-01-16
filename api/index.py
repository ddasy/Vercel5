import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mangum import adapter
from app.main import app

# Create handler for Vercel serverless deployment with lifespan disabled for better cold starts
handler = adapter(app, lifespan="off")
