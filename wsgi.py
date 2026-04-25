"""
WSGI entry point for Render.com, Heroku, and other cloud deployments.
This file tells the WSGI server (Gunicorn) how to run your Flask application.

For local development: python server.py
For production: gunicorn wsgi:app
"""

import os
from server_post import app

if __name__ == "__main__":
    # This is only for local testing - production uses gunicorn
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
