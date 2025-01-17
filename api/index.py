import sys
import os
import logging
from mangum import Mangum
from app.main import app

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

# Create handler
handler = Mangum(app, lifespan="off")
