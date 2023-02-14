import os
from dotenv import load_dotenv

# Flask app config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

FLASK_ENV = 'development'
TESTING = True
SECRET_KEY = os.environ.get('SECRET_KEY')
JSON_SORT_KEYS = False
DEBUG = True