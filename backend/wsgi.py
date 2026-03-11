"""WSGI application for Gunicorn"""
from app import create_app
import os

# Create the Flask app
app = create_app(config_name=os.getenv('FLASK_ENV', 'development'))

if __name__ == "__main__":
    app.run()
