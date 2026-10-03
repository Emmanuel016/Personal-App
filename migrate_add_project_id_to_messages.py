"""
Migration script to add project_id column to messages table
This links order messages to their corresponding projects
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
    """Add project_id column to messages table"""
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
            columns = [col['name'] for col in inspector.get_columns('messages')]
            
            if 'project_id' in columns:
                print("Column 'project_id' already exists in messages table")
                return
            
            # Add the column
            with db.engine.connect() as conn:
                if database_url.startswith("sqlite"):
                    conn.execute(text("ALTER TABLE messages ADD COLUMN project_id INTEGER"))
                else:
                    conn.execute(text("ALTER TABLE messages ADD COLUMN project_id INTEGER REFERENCES projects(id)"))
                conn.commit()
            
            print("Successfully added project_id column to messages table")
            
            # Link existing order messages to their projects by matching service name in message content
            # This is a best-effort migration for existing data
            print("Attempting to link existing order messages to projects...")
            with db.engine.connect() as conn:
                # For SQLite, foreign key constraints need special handling
                if database_url.startswith("sqlite"):
                    conn.execute(text("PRAGMA foreign_keys=OFF"))
                
                # Update messages that match the pattern "NEW ORDER: Client 'X' placed order for 'ServiceName'"
                # by matching the service name to project titles
                result = conn.execute(text("""
                    UPDATE messages 
                    SET project_id = (
                        SELECT id FROM projects 
                        WHERE projects.title = SUBSTR(
                            SUBSTR(messages.content, INSTR(messages.content, 'placed order for ''') + 18),
                            0,
                            INSTR(SUBSTR(messages.content, INSTR(messages.content, 'placed order for ''') + 18), ''')
                        )
                    )
                    WHERE messages.content LIKE '%placed order for%'
                    AND project_id IS NULL
                """))
                conn.commit()
                
                if database_url.startswith("sqlite"):
                    conn.execute(text("PRAGMA foreign_keys=ON"))
                
                print(f"Linked {result.rowcount} order messages to their projects")
            
        except Exception as e:
            print(f"Error during migration: {e}")
            sys.exit(1)

if __name__ == "__main__":
    migrate()
