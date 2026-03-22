"""WSGI application for Gunicorn"""
from app import create_app
from extensions import socketio
import os

# Create the Flask app
app = create_app(config_name=os.getenv('FLASK_ENV', 'development'))

if __name__ == "__main__":
    socketio.run(app)
