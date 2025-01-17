import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)
    logger.info(f"Python path set to: {project_root}")
logger.info(f"Current sys.path: {sys.path}")

try:
    from mangum.adapter import Mangum
    logger.info("Successfully imported mangum")
except ImportError as e:
    logger.error(f"Failed to import mangum: {str(e)}")
    raise

try:
    from app.main import app
    logger.info("Successfully imported FastAPI app")
except ImportError as e:
    logger.error(f"Failed to import FastAPI app: {str(e)}")
    raise

try:
    handler = Mangum(app=app, lifespan="off")
    logger.info("Successfully created Mangum handler")
except Exception as e:
    logger.error(f"Error initializing application: {str(e)}")
    raise
