# wsgi.py — Production Entrypoint for Render
import os
from server import EmmaServer
from models import db, DatabaseManager

# Instantiate server (loads config, routes, managers, limiter, scheduler, socketio)
server = EmmaServer()

# Initialize database BEFORE serving requests
with server.app.app_context():
    DatabaseManager.initialize_database(server.app, db)

# Expose WSGI application for Render
app = server.app

# Optional local development runner
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

    # IMPORTANT:
    # For local testing we run Flask directly.
    # In production Render uses Gunicorn → which imports `app` above.
    server.run(host="0.0.0.0", port=port, debug=debug_mode, use_reloader=False)