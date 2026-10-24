import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class Config:
    """
    Application Configuration
    Contains database and Flask configuration settings.
    """
    # Flask Secret Key for session security
    SECRET_KEY = os.environ.get('SECRET_KEY', 'village_service_secret_key_bca_2026')

    # MySQL Database Configuration
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'sarvesh07')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'village_service_db')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_CURSORCLASS = 'DictCursor'
