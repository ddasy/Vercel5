import os
import sys
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the project root to Python path
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    sys.path.insert(0, project_root)
    logger.info(f"Python path set to: {project_root}")
    logger.info(f"Current sys.path: {sys.path}")
except Exception as e:
    logger.error(f"Error setting Python path: {str(e)}\n{traceback.format_exc()}")
    raise

try:
    from mangum import adapter
    logger.info("Successfully imported mangum")
    from app.main import app
    logger.info("Successfully imported FastAPI app")
    
    # Create handler for Vercel serverless deployment
    handler = adapter(app, lifespan="off")
    logger.info("FastAPI application and handler initialized successfully")
except Exception as e:
    logger.error(f"Error initializing application: {str(e)}\n{traceback.format_exc()}")
    raise
