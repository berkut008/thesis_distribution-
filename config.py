import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-12345'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///thesis.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'uploads'
    EXPORT_FOLDER = 'exports'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    RESERVATION_TIMEOUT = 1800  # 30 минут