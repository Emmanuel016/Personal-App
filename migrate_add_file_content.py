"""
Migration script to add file_content column to file_attachments table
Run this script to add the new column for storing file content in the database
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
    """Add file_content column to file_attachments table"""
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
            # Check if column already exists
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('file_attachments')]
            
            if 'file_content' in columns:
                print("Column 'file_content' already exists in file_attachments table")
                return
            
            # Add the column
            with db.engine.connect() as conn:
                if database_url.startswith("sqlite"):
                    conn.execute(text("ALTER TABLE file_attachments ADD COLUMN file_content BLOB"))
                else:
                    conn.execute(text("ALTER TABLE file_attachments ADD COLUMN file_content BYTEA"))
                conn.commit()
            
            print("Successfully added file_content column to file_attachments table")
            
        except Exception as e:
            print(f"Error during migration: {e}")
            sys.exit(1)

if __name__ == "__main__":
    migrate()
