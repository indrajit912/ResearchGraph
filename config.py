import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-fallback-change-in-prod')
    
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'researchgraph.db')}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Hermes Email Integration
    HERMES_API_URL = os.environ.get('HERMES_API_URL', 'https://hermesbot.pythonanywhere.com')
    HERMES_API_KEY = os.environ.get('HERMES_API_KEY')
    HERMES_EMAILBOT_ID = os.environ.get('HERMES_EMAILBOT_ID')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    # Ensure SECRET_KEY is set in environment for production
    SECRET_KEY = os.environ.get('SECRET_KEY')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
