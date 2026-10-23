"""
Migration script to add soft delete columns (deleted_at, is_active) to existing tables
This prevents accidental data loss and enables data recovery
"""
import os
import sys
from datetime import datetime, timezone
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

# Load environment
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# Configure database
configured_database_url = os.environ.get("DATABASE_URL", "").strip()
use_local_database = os.environ.get("USE_LOCAL_DATABASE", "true").strip().lower() in ("1", "true", "yes", "on")

if use_local_database or not configured_database_url:
    instance_dir = os.path.join(os.path.dirname(__file__), "instance")
    os.makedirs(instance_dir, exist_ok=True)
    local_database_path = os.path.join(instance_dir, "personal-app-db.db")
    database_url = f"sqlite:///{local_database_path}"
    print(f"Using local SQLite database: {local_database_path}")
else:
    database_url = configured_database_url
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    print(f"Using PostgreSQL database")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

def migrate():
    """Add soft delete columns to all relevant tables"""
    with app.app_context():
        print("Starting soft delete migration...")
        
        try:
            # Add deleted_at and is_active to users table
            print("Adding deleted_at and is_active to users table...")
            try:
                db.session.execute(text("ALTER TABLE users ADD COLUMN deleted_at DATETIME"))
                print("  - Added deleted_at column to users")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print("  - deleted_at column already exists in users")
                else:
                    raise
            
            try:
                db.session.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1"))
                print("  - Added is_active column to users")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print("  - is_active column already exists in users")
                else:
                    raise
            
            # Add deleted_at to projects table
            print("Adding deleted_at to projects table...")
            try:
                db.session.execute(text("ALTER TABLE projects ADD COLUMN deleted_at DATETIME"))
                print("  - Added deleted_at column to projects")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print("  - deleted_at column already exists in projects")
                else:
                    raise
            
            # Add deleted_at to messages table
            print("Adding deleted_at to messages table...")
            try:
                db.session.execute(text("ALTER TABLE messages ADD COLUMN deleted_at DATETIME"))
                print("  - Added deleted_at column to messages")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print("  - deleted_at column already exists in messages")
                else:
                    raise
            
            # Add deleted_at to file_attachments table
            print("Adding deleted_at to file_attachments table...")
            try:
                db.session.execute(text("ALTER TABLE file_attachments ADD COLUMN deleted_at DATETIME"))
                print("  - Added deleted_at column to file_attachments")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print("  - deleted_at column already exists in file_attachments")
                else:
                    raise
            
            # Add deleted_at to invoices table
            print("Adding deleted_at to invoices table...")
            try:
                db.session.execute(text("ALTER TABLE invoices ADD COLUMN deleted_at DATETIME"))
                print("  - Added deleted_at column to invoices")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print("  - deleted_at column already exists in invoices")
                else:
                    raise
            
            db.session.commit()
            print("\n[OK] Soft delete migration completed successfully!")
            print("\nNew columns added:")
            print("  - users.deleted_at (DATETIME)")
            print("  - users.is_active (BOOLEAN)")
            print("  - projects.deleted_at (DATETIME)")
            print("  - messages.deleted_at (DATETIME)")
            print("  - file_attachments.deleted_at (DATETIME)")
            print("  - invoices.deleted_at (DATETIME)")
            print("\nThese columns enable soft delete functionality and prevent accidental data loss.")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] Migration failed: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    migrate()
