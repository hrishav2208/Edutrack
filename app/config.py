"""App configuration — profiles for development, testing, and production."""

import os

# Base directory is one level up if config.py is placed inside the app/ package
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "edutrack-dev-key-change-for-production"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        "sqlite:///" + os.path.join(INSTANCE_DIR, "edutrack.db")
    )
    
    # If the database URL starts with postgres://, replace with postgresql:// for SQLAlchemy compatibility
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Default campus center (neutral); admin can update in app — radius in metres
    DEFAULT_CAMPUS_LAT = float(os.environ.get("EDUTRACK_CAMPUS_LAT", "20.5937"))
    DEFAULT_CAMPUS_LNG = float(os.environ.get("EDUTRACK_CAMPUS_LNG", "78.9629"))
    DEFAULT_CAMPUS_RADIUS_M = float(os.environ.get("EDUTRACK_CAMPUS_RADIUS_M", "500"))


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    # Enforce cookies over HTTPS if SSL is set up
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() in ("true", "1", "yes")


config_by_name = {
    "dev": DevelopmentConfig,
    "test": TestingConfig,
    "prod": ProductionConfig,
}
