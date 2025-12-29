"""
WSGI application entry point for gunicorn
"""
from server import app

if __name__ == "__main__":
    app.run()
