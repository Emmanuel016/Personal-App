"""
Migration script to remove file_content column from file_attachments table
Run this script to remove the legacy column after migrating to disk-only storage
"""
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import text, inspect
from flask import Flask
from models import db

# Load environment variables
load_dotenv()

def migrate():
    """Remove file_content column from file_attachments table"""
    app = Flask(__name__)
    
    # Get database URL from environment
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    if not database_url:
        database_url = "sqlite:///personalapp.db"
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        try:
            # Check if column exists
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('file_attachments')]
            
            if 'file_content' not in columns:
                print("Column 'file_content' does not exist in file_attachments table")
                return
            
            # Drop the column
            with db.engine.connect() as conn:
                if database_url.startswith("sqlite"):
                    conn.execute(text("ALTER TABLE file_attachments DROP COLUMN file_content"))
                else:
                    conn.execute(text("ALTER TABLE file_attachments DROP COLUMN file_content"))
                conn.commit()
            
            print("Successfully removed file_content column from file_attachments table")
            
        except Exception as e:
            print(f"Error during migration: {e}")
            sys.exit(1)

if __name__ == "__main__":
    migrate()
