import logging
from datetime import datetime, date, timezone, timedelta
from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy explicitly
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=True)
    role = db.Column(db.String(50), default="client")
    email = db.Column(db.String(255))
    company = db.Column(db.String(255))
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    country = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    type = db.Column(db.String(50))
    date_added = db.Column(db.Date)

    projects = db.relationship("Project", backref="client", lazy=True, cascade="all, delete-orphan")
    messages = db.relationship("Message", backref="client_user", lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship("Notification", backref="user", lazy=True, cascade="all, delete-orphan")
    invoices = db.relationship("Invoice", backref="client", lazy=True, cascade="all, delete-orphan")
    notification_preferences = db.relationship("NotificationPreference", backref="user", lazy=True, cascade="all, delete-orphan")
    password_reset_tokens = db.relationship("PasswordResetToken", backref="user", lazy=True, cascade="all, delete-orphan")

class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    client_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    client_name = db.Column(db.String(150))
    title = db.Column(db.String(255))
    desc = db.Column(db.Text)
    budget_estimate = db.Column(db.String(100))
    status = db.Column(db.String(100), default="Pending Approval")
    date_created = db.Column(db.Date, default=date.today)
    deadline = db.Column(db.Date)
    amount_paid = db.Column(db.Float, default=0.0)
    price = db.Column(db.Float, default=0.0)
    
    invoices = db.relationship("Invoice", backref="project", lazy=True, cascade="all, delete-orphan")

class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    from_role = db.Column("sender_role", db.String(50))
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    type = db.Column(db.String(50))
    payment_data = db.Column(db.JSON)
    
    attachments = db.relationship("FileAttachment", backref="message", lazy=True, cascade="all, delete-orphan")

class Service(db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, default=0.0)
    icon = db.Column(db.String(100))

class Feedback(db.Model):
    __tablename__ = "feedback"
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(255), nullable=False)
    client_email = db.Column(db.String(255))
    service_category = db.Column(db.String(255), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class FileAttachment(db.Model):
    __tablename__ = "file_attachments"
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey("messages.id"), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    uploaded_by_role = db.Column(db.String(50))
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    target_role = db.Column(db.String(50), nullable=False, default="client")
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    data = db.Column(db.JSON)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        db.Index('idx_notification_user_read', 'user_id', 'read'),
        db.Index('idx_notification_target_role', 'target_role'),
    )

class NotificationPreference(db.Model):
    __tablename__ = "notification_preferences"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    browser_enabled = db.Column(db.Boolean, default=True)
    email_enabled = db.Column(db.Boolean, default=False)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'notification_type', name='unique_user_notification_type'),
        db.Index('idx_notification_preference_user', 'user_id'),
    )

class Invoice(db.Model):
    __tablename__ = "invoices"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    invoice_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), default="pending")
    items = db.Column(db.JSON)
    payment_terms = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    paid_at = db.Column(db.DateTime)
    reminder_sent_at = db.Column(db.DateTime)
    
    __table_args__ = (
        db.Index('idx_invoice_status', 'status'),
        db.Index('idx_invoice_client', 'client_id'),
        db.Index('idx_invoice_project', 'project_id'),
        db.Index('idx_invoice_due_date', 'due_date'),
    )

class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index('idx_reset_token_user', 'user_id'),
        db.Index('idx_reset_token_expires', 'expires_at'),
    )

class DatabaseManager:
    """OOP encapsulation for Database initializations"""
    @staticmethod
    def initialize_database(app, database_instance):
        logger = logging.getLogger(__name__)
        try:
            logger.info("Initializing database...")
            with app.app_context():
                database_instance.create_all()
                logger.info("Database tables created/verified successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            raise