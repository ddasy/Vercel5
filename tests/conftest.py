import pytest
import os
from dotenv import load_dotenv

@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables."""
    # Load test environment variables
    load_dotenv(".env.test", override=True)
    
    # Set test environment variables
    os.environ["WEBHOOK_SECRET"] = "test_webhook_secret"
    os.environ["OKX_API_KEY"] = "test_api_key"
    os.environ["OKX_SECRET_KEY"] = "test_secret_key"
    os.environ["OKX_PASSPHRASE"] = "test_passphrase"
    os.environ["OKX_API_URL"] = "https://www.okx.com"
    
    yield
    
    # Clean up
    os.environ.pop("WEBHOOK_SECRET", None)
    os.environ.pop("OKX_API_KEY", None)
    os.environ.pop("OKX_SECRET_KEY", None)
    os.environ.pop("OKX_PASSPHRASE", None)
    os.environ.pop("OKX_API_URL", None)
