from mangum import adapter
from app.main import app

# Create handler for Vercel serverless deployment
handler = adapter(app)
