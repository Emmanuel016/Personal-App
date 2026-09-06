import os
import re
import secrets
import bcrypt
import logging
import requests
import base64
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from io import BytesIO
from dotenv import load_dotenv
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Flask, jsonify, request, render_template, redirect, session, url_for, send_file, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_mail import Mail, Message as MailMessage # Renamed to prevent model naming collisions
from apscheduler.schedulers.background import BackgroundScheduler
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from functools import wraps

# Import Database Schema & Manager
from models import db, User, Project, Message, Service, Feedback, FileAttachment, Notification, NotificationPreference, Invoice, PasswordResetToken, DatabaseManager

# Load .env configurations
load_dotenv()

# Configure logging
try:
    LOG_DIR = Path(__file__).resolve().parent / "logs"
    LOG_DIR.mkdir(exist_ok=True)
    
    # Configure root logger for better control
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Enhanced format with timestamp, module, and level
    log_format = logging.Formatter("%(levelname)s | %(message)s")
    #log_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    
    # Rotating file handler (100MB max, keep 5 backups)
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=100*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)
    
    # Stream handler for console (INFO level to reduce noise)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(log_format)
    
    # Clear existing handlers and add new ones (avoid duplicates)
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)
    
    # Create module-specific logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    
except Exception as e:
    # Fallback to basic logging if directory creation fails
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to configure logging directory: {e}. Using basic logging.")
 


class AppConfig:
    """OOP Encapsulation for Configurations and Server Constants"""
    BASE_DIR = Path(__file__).resolve().parent
    ALLOWED_EXTENSIONS = {
        'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'xml', 'avi', 'mov', 'mkv', 'md', 'webp', 'cpp',
        'doc', 'html', 'docx', 'xls', 'xlsx', 'json', 'zip', 'ppt', 'pptx', 'webm', 'mp3', 'wav', 'csv', 'css', 'py'
    }
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    
    def __init__(self):
        # Environment detection
        self.is_production_env = (
            os.environ.get("FLASK_ENV", "").lower() == "production" or
            os.environ.get("ENV", "").lower() == "production" or
            os.environ.get("PRODUCTION", "").lower() in ("1", "true", "yes")
        )
        
        # Use persistent disk mount path in production (Render/Heroku)
        if self.is_production_env:
            self.UPLOADS_DIR = Path("/opt/render/project/uploads")
        else:
            self.UPLOADS_DIR = self.BASE_DIR / 'uploads'
        
        self.PDF_CACHE_DIR = self.BASE_DIR / 'pdf_cache'

        # Persistent secret key loading logic
        SECRET_KEY_FILE = self.BASE_DIR / ".flask_secret_key"
        env_secret = os.environ.get("FLASK_SECRET_KEY")

        if env_secret:
            self.SECRET_KEY = env_secret
        else:
            if SECRET_KEY_FILE.exists():
                self.SECRET_KEY = SECRET_KEY_FILE.read_text().strip()
            else:
                generated_key = secrets.token_hex(32)
                try:
                    SECRET_KEY_FILE.write_text(generated_key)
                    self.SECRET_KEY = generated_key
                except Exception as e:
                    logger.warning(f"Could not save persistent secret key: {e}. Falling back to single-session key.")
                    self.SECRET_KEY = generated_key

        # SQL Configuration
        self.DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
        if self.DATABASE_URL:
            if self.DATABASE_URL.startswith("postgres://"):
                self.DATABASE_URL = self.DATABASE_URL.replace("postgres://", "postgresql://", 1)
            if self.DATABASE_URL.startswith("postgresql://") and "sslmode=" not in self.DATABASE_URL:
                if any(host in self.DATABASE_URL for host in ("render.com", "heroku", "aws")):
                    sep = "&" if "?" in self.DATABASE_URL else "?"
                    self.DATABASE_URL = f"{self.DATABASE_URL}{sep}sslmode=require"
        else:
            if self.is_production_env:
                raise RuntimeError("DATABASE_URL must be set in production environment")
            self.DATABASE_URL = "sqlite:///personalapp.db"

        self.secure_session_cookie = self.is_production_env or os.environ.get("HTTPS_ONLY", "").lower() in ("1", "true", "yes")
        self.allowed_origins = os.environ.get('ALLOWED_ORIGINS', '*').split(',')

        # PayPal configuration variables
        self.PAYPAL_MODE = os.environ.get("PAYPAL_MODE", "sandbox")
        self.PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
        self.PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
        self.PAYPAL_API_BASE = "https://api.sandbox.paypal.com" if self.PAYPAL_MODE == "sandbox" else "https://api.paypal.com"

        self.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        self.PDF_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def apply_to_app(self, app):
        """Applies dynamic properties to the active Flask application context"""
        app.secret_key = self.SECRET_KEY
        app.config.update(
            SESSION_COOKIE_SECURE=self.secure_session_cookie,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
            PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
            SESSION_COOKIE_NAME='__Secure-personal_app_session' if self.secure_session_cookie else 'personal_app_session',
            WTF_CSRF_ENABLED=True,
            WTF_CSRF_TIME_LIMIT=3600,
            SEND_FILE_MAX_AGE_DEFAULT=31536000,
            MAX_CONTENT_LENGTH=self.MAX_FILE_SIZE,
            SQLALCHEMY_DATABASE_URI=self.DATABASE_URL,
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            MAIL_SERVER=os.environ.get('MAIL_SERVER', 'smtp.gmail.com'),
            MAIL_PORT=int(os.environ.get('MAIL_PORT', 587)),
            MAIL_USE_TLS=os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', 'on', '1'],
            MAIL_USERNAME=os.environ.get('MAIL_USERNAME', ''),
            MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD', ''),
            MAIL_DEFAULT_SENDER=os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@emmastudio.com')
        )


class SecurityManager:
    """OOP Encapsulation for Security utilities and Access Control decorators"""
    @staticmethod
    def hash_password(password: str) -> str:
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    @staticmethod
    def validate_username(username: str) -> bool:
        if not username or len(username) < 3 or len(username) > 50: return False
        return bool(re.match(r'^[a-zA-Z0-9\-_]+$', username))

    @staticmethod
    def validate_password(password: str):
        if not password: return False, "Password is required"
        if len(password) < 5: return False, "Password must be at least 5 characters"
        if len(password) > 128: return False, "Password must not exceed 128 characters"
        if not any(c.isdigit() for c in password): return False, "Password must contain numbers"
        return True, ""

    @staticmethod
    def validate_email(email: str) -> bool:
        if not email: return True
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return len(email) <= 255 and bool(re.match(pattern, email))

    @staticmethod
    def validate_project_title(title: str) -> bool:
        return bool(title) and 3 <= len(title) <= 255

    @staticmethod
    def validate_amount(amount: float) -> bool:
        try: return 0.01 <= float(amount) <= 999999.99
        except (ValueError, TypeError): return False

    @staticmethod
    def validate_rating(rating: int) -> bool:
        try: return 1 <= int(rating) <= 5
        except (ValueError, TypeError): return False

    @staticmethod
    def sanitize_input(input_string: str) -> str:
        if not input_string: return ""
        return re.sub(r'<[^>]*>', '', input_string).strip()

    @staticmethod
    def generate_reset_token() -> str:
        """Generate a cryptographically secure random token for password reset"""
        return secrets.token_urlsafe(48)

    @staticmethod
    def validate_reset_token(token: str) -> tuple[bool, str]:
        """Validate a password reset token and return (is_valid, error_message)"""
        if not token or len(token) < 32:
            return False, "Invalid token format"
        return True, ""

    @staticmethod
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in AppConfig.ALLOWED_EXTENSIONS

    @staticmethod
    def get_safe_file_path(filename: str, uploads_dir: Path) -> Path:
        # Skip secure_filename for already-sanitized stored filenames (contain timestamp prefix)
        # These are generated by our upload system and are safe
        if filename and re.match(r'^\d{8}_\d{6}_[a-f0-9]+_', filename):
            clean_filename = filename
        else:
            clean_filename = secure_filename(filename)
        
        if not clean_filename:
            abort(400, "Invalid file name")
        resolved_path = (uploads_dir / clean_filename).resolve()
        if not resolved_path.is_relative_to(uploads_dir.resolve()):
            logger.error(f"Directory traversal attempt detected! Path: {resolved_path}")
            abort(400, "Directory traversal path attempt detected!")
        return resolved_path

    @staticmethod
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get("user_id")
            if not user_id:
                logger.warning(f"Unauthorized access attempt blocked from IP {get_remote_address()} on route {request.path}")
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({"error": "Unauthorized"}), 401
                return redirect(url_for("login"))
            user = db.session.get(User, user_id)
            if not user:
                session.clear()
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({"error": "User account no longer exists"}), 401
                return redirect(url_for("login"))
            session["last_activity"] = datetime.now(timezone.utc).isoformat()
            return f(*args, **kwargs)
        return decorated_function

    @staticmethod
    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get("user_id")
            role = session.get("role")
            if not user_id or not role or role.lower() != "admin":
                logger.warning(f"Access Denied: Non-admin {user_id} attempted access to administrative route {request.path}")
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({"error": "Forbidden"}), 403
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return decorated_function


class CommunicationManager:
    """OOP Service for Email and WebSocket notifications"""
    def __init__(self, app, mail_instance, socketio_instance, db_instance, config):
        self.app = app
        self.mail = mail_instance
        self.socketio = socketio_instance
        self.db = db_instance
        self.config = config

    def send_notification(self, user_id, notification_type, title, message, data=None, target_role="client"):
        try:
            # Check user notification preferences
            preference = NotificationPreference.query.filter_by(
                user_id=user_id, 
                notification_type=notification_type
            ).first()
            
            # If preference exists and is disabled, skip notification
            if preference and not preference.enabled:
                logger.info(f"Notification type {notification_type} disabled for user {user_id}, skipping")
                return None
            
            notification = Notification(
                user_id=user_id,
                target_role=target_role,
                type=notification_type,
                title=title,
                message=message,
                data=data or {}
            )
            self.db.session.add(notification)
            self.db.session.commit()
            
            notification_data = {
                'id': notification.id,
                'type': notification.type,
                'title': notification.title,
                'message': notification.message,
                'data': notification.data,
                'read': notification.read,
                'created_at': notification.created_at.isoformat()
            }
            
            # Send WebSocket notification if browser notifications enabled
            if not preference or preference.browser_enabled:
                self.socketio.emit('new_notification', notification_data, room=f'user_{user_id}')
            
            logger.info(f"Notification sent to user {user_id} (role: {target_role}): {title}")
            return notification
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            self.db.session.rollback()
            return None

    def send_invoice_email(self, invoice, payment_methods=None, late_fee=None, early_discount=None):
        try:
            if not self.app.config['MAIL_USERNAME']:
                logger.warning("Email not configured, skipping invoice email")
                return
            client = db.session.get(User, invoice.client_id)
            if not client or not client.email:
                logger.warning(f"Client {invoice.client_id} has no email address")
                return
            
            subject = f"Invoice {invoice.invoice_number} - Payment Required"
            pm = payment_methods or os.environ.get('PAYMENT_METHODS', 'PayPal, Bank Transfer')
            lf = late_fee or os.environ.get('LATE_FEE', '5% per month on overdue amount')
            ed = early_discount or os.environ.get('EARLY_DISCOUNT', '2% discount if paid within 10 days')
            # Calculate actual total cost from items
            actual_total_cost = 0.0
            if invoice.items:
                for item in invoice.items:
                    actual_total_cost += item.get('quantity', 1) * item.get('price', 0)
            else:
                actual_total_cost = invoice.amount
            
            html_body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #0a192f; color: #00f2fe; padding: 20px; text-align: center; }}
                    .content {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
                    .invoice-details {{ background: white; padding: 15px; margin: 15px 0; border-radius: 5px; }}
                    .total {{ font-size: 24px; font-weight: bold; color: #00f2fe; }}
                    .button {{ display: inline-block; padding: 12px 24px; background: #00f2fe; color: #0a192f; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                    .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
                    .payment-info {{ background: #e8f4f8; padding: 15px; margin: 15px 0; border-radius: 5px; border-left: 4px solid #00f2fe; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header"><h1>EmmaStudio</h1><p>Professional Freelancing Services</p></div>
                    <div class="content">
                        <h2>Invoice {invoice.invoice_number}</h2>
                        <p>Dear {client.username},</p>
                        <p>A new invoice has been generated for your project.</p>
                        <div class="invoice-details">
                            <p><strong>Invoice Number:</strong> {invoice.invoice_number}</p>
                            <p><strong>Date of Issue:</strong> {invoice.created_at.strftime('%B %d, %Y')}</p>
                            <p><strong>Due Date:</strong> {invoice.due_date.strftime('%B %d, %Y')}</p>
                            <p><strong>Total Amount:</strong> <span class="total">£{actual_total_cost:.2f}</span></p>
                            <p><strong>Amount Due:</strong> <span class="total">£{invoice.amount:.2f}</span></p>
                            <p><strong>Payment Terms:</strong> {invoice.payment_terms}</p>
                        </div>
                        <div class="payment-info">
                            <h3>Payment Information</h3>
                            <p><strong>Accepted Payment Methods:</strong> {pm}</p>
                            <p><strong>Late Fee:</strong> {lf}</p>
                            <p><strong>Early Payment Discount:</strong> {ed}</p>
                        </div>
                        <p>To pay this invoice, click the button below:</p>
                        <p style="text-align: center;"><a href="https://emma-studio.onrender.com/api/invoices/{invoice.id}/pdf" class="button">Download PDF</a></p>
                        <p style="text-align: center;"><a href="https://emma-studio.onrender.com/api/invoices/{invoice.id}/pay" class="button">Pay Now</a></p>
                    </div>
                </div>
            </body>
            </html>"""
            
            msg = MailMessage(subject=subject, recipients=[client.email], html=html_body)
            self.mail.send(msg)
            logger.info(f"Invoice email sent to {client.email} for invoice {invoice.invoice_number}")
        except Exception as e:
            logger.error(f"Error sending invoice email: {str(e)}")

    def send_reminder_email(self, invoice):
        try:
            if not self.app.config['MAIL_USERNAME']: return
            client = db.session.get(User, invoice.client_id)
            if not client or not client.email: return
            
            if not invoice.due_date:
                logger.warning(f"Invoice {invoice.invoice_number} has no due date, skipping reminder")
                return
            
            days_until_due = (invoice.due_date - date.today()).days
            days_text = f"{abs(days_until_due)} days overdue" if days_until_due < 0 else f"{days_until_due} days until due"
            subject = f"Payment Reminder: Invoice {invoice.invoice_number}"
            
            html_body = f"""
            <html>
            <body>
                <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;">
                    <div style="background:#0a192f;color:#00f2fe;padding:20px;text-align:center;"><h1>EmmaStudio</h1><p>Payment Reminder</p></div>
                    <div style="background:#f5f5f5;padding:20px;">
                        <h2>Invoice {invoice.invoice_number}</h2>
                        <p>Dear {client.username},</p>
                        <div style="background:#fff3cd;padding:15px;border-left:4px solid #ffc107;"><strong>Reminder:</strong> Your invoice is {days_text}.</div>
                        <ul><li>Amount Due: £{invoice.amount:.2f}</li></ul>
                        <p style="text-align:center;"><a href="https://emma-studio5.onrender.com/api/invoices/{invoice.id}/pay" style="display:inline-block;padding:12px 24px;background:#00f2fe;color:#0a192f;text-decoration:none;font-weight:bold;">Pay Now</a></p>
                    </div>
                </div>
            </body>
            </html>"""
            
            msg = MailMessage(subject=subject, recipients=[client.email], html=html_body)
            self.mail.send(msg)
            logger.info(f"Reminder email sent to {client.email} for invoice {invoice.invoice_number}")
            invoice.reminder_sent_at = datetime.now(timezone.utc)
            self.db.session.commit()
        except Exception as e:
            logger.error(f"Error sending reminder email: {str(e)}")

    def send_password_reset_email(self, email, token):
        """Send password reset email with secure token link"""
        try:
            if not self.app.config['MAIL_USERNAME']:
                logger.warning("Email not configured, skipping password reset email")
                return

            # Generate reset link - using the current request's host for proper URL generation
            from flask import request
            reset_link = f"{request.url_root}reset-password/{token}"

            # Get support email from config
            support_email = os.environ.get('COMPANY_EMAIL', 'support@emmastudio.com')

            # Render email template
            html_body = render_template('password_reset_email.html', 
                                        reset_link=reset_link, 
                                        support_email=support_email)

            subject = "Password Reset Request - EMMA.STUDIO"
            msg = MailMessage(subject=subject, recipients=[email], html=html_body)
            self.mail.send(msg)
            logger.info(f"Password reset email sent to {email}")
        except Exception as e:
            logger.error(f"Error sending password reset email: {str(e)}")
            raise


class FinanceManager:
    """OOP Service for Payments, Invoices, and Scheduling"""
    def __init__(self, app, comms_manager, db_instance, config):
        self.app = app
        self.comms = comms_manager
        self.db = db_instance
        self.config = config

    def get_pdf_cache_path(self, invoice_id):
        """Generate cache file path for invoice PDF"""
        return self.config.PDF_CACHE_DIR / f"invoice_{invoice_id}.pdf"

    def is_pdf_cached(self, invoice_id):
        """Check if PDF exists in cache and is valid"""
        cache_path = self.get_pdf_cache_path(invoice_id)
        if not cache_path.exists():
            return False
        
        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            return False
        
        cache_mtime = cache_path.stat().st_mtime
        invoice_mtime = invoice.updated_at.timestamp() if hasattr(invoice, 'updated_at') else invoice.created_at.timestamp()
        
        return cache_mtime > invoice_mtime

    def invalidate_pdf_cache(self, invoice_id):
        """Remove cached PDF if it exists"""
        cache_path = self.get_pdf_cache_path(invoice_id)
        if cache_path.exists():
            cache_path.unlink()
            logger.info(f"Invalidated PDF cache for invoice {invoice_id}")

    def get_paypal_access_token(self):
        if not self.config.PAYPAL_CLIENT_ID or not self.config.PAYPAL_CLIENT_SECRET:
            logger.error("PayPal credentials not configured")
            return None
        try:
            auth = base64.b64encode(f"{self.config.PAYPAL_CLIENT_ID}:{self.config.PAYPAL_CLIENT_SECRET}".encode()).decode()
            headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"}
            response = requests.post(f"{self.config.PAYPAL_API_BASE}/v1/oauth2/token", headers=headers, data={"grant_type": "client_credentials"}, timeout=10)
            if response.status_code == 200: return response.json().get("access_token")
            return None
        except Exception as e:
            logger.error(f"Error getting PayPal token: {str(e)}")
            return None

    def generate_invoice_number(self):
        prefix = os.environ.get('INVOICE_PREFIX', 'INV-')
        return f"{prefix}{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"

    def generate_invoice(self, project_id, invoice_type):
        try:
            project = db.session.get(Project, project_id)
            if not project: return None
            
            existing = Invoice.query.filter_by(project_id=project_id, invoice_type=invoice_type, status='pending').first()
            if existing: return existing
            
            amount = (project.price - project.amount_paid) if invoice_type == 'completion' else (project.price * 0.5)
            if amount <= 0: return None
            
            due_days = int(os.environ.get('INVOICE_DUE_DAYS', 30))
            due_date = date.today() + timedelta(days=due_days)
            items = [{'description': f"{project.title} - {invoice_type.title()} Invoice", 'quantity': 1, 'price': amount}]
            
            invoice = Invoice(
                project_id=project_id, client_id=project.client_user_id,
                invoice_number=self.generate_invoice_number(), invoice_type=invoice_type,
                amount=amount, due_date=due_date, status='pending', items=items,
                payment_terms=f"Payment due within {due_days} days", notes="Thank you for your business!"
            )
            self.db.session.add(invoice)
            self.db.session.commit()
            
            self.comms.send_notification(
                user_id=project.client_user_id, notification_type="payment",
                title="New Invoice Generated", message=f"Invoice {invoice.invoice_number} has been generated. Amount: ${amount:.2f}",
                data={"invoice_id": invoice.id, "invoice_number": invoice.invoice_number, "amount": amount}
            )
            self.comms.send_invoice_email(invoice)
            return invoice
        except Exception as e:
            logger.error(f"Error generating invoice: {str(e)}")
            self.db.session.rollback()
            return None

    def check_invoice_reminders(self):
        try:
            with self.app.app_context():
                today = date.today()
                for invoice in Invoice.query.filter_by(status='pending').all():
                    days_until_due = (invoice.due_date - today).days
                    reminder_days = [int(d) for d in os.environ.get('INVOICE_REMINDER_SCHEDULE', '7,1,-1,-7').split(',')]
                    
                    if days_until_due in reminder_days:
                        if invoice.reminder_sent_at and (today - invoice.reminder_sent_at.date()).days < 1:
                            continue
                        try:
                            self.comms.send_reminder_email(invoice)
                        except Exception as email_error:
                            logger.error(f"Failed to send reminder email for invoice {invoice.invoice_number}: {str(email_error)}")
                    
                    if days_until_due < 0 and invoice.status == 'pending':
                        invoice.status = 'overdue'
                        self.db.session.commit()
        except Exception as e:
            logger.error(f"Error in scheduled reminder check: {str(e)}")

    def check_deadline_reminders(self):
        try:
            with self.app.app_context():
                today = date.today()
                reminder_days = [int(d) for d in os.environ.get('DEADLINE_REMINDER_SCHEDULE', '7,3,1,-1').split(',')]
                
                for project in Project.query.filter(Project.status != 'Completed').all():
                    if not project.deadline:
                        continue
                    
                    days_until_deadline = (project.deadline - today).days
                    
                    if days_until_deadline in reminder_days:
                        last_reminder_key = f'deadline_reminder_{project.id}_{days_until_deadline}'
                        # Simple check to avoid duplicate reminders on same day
                        if hasattr(self, '_deadline_reminders') and last_reminder_key in self._deadline_reminders:
                            if (self._deadline_reminders[last_reminder_key] - today).days == 0:
                                continue
                        
                        days_text = f"{abs(days_until_deadline)} days overdue" if days_until_deadline < 0 else f"{days_until_deadline} days until deadline"
                        
                        self.comms.send_notification(
                            user_id=project.client_user_id,
                            notification_type="deadline_reminder",
                            title=f"Project Deadline Reminder",
                            message=f"Project '{project.title}' deadline is {days_text}",
                            data={"project_id": project.id, "deadline": project.deadline.isoformat()}
                        )
                        
                        if not hasattr(self, '_deadline_reminders'):
                            self._deadline_reminders = {}
                        self._deadline_reminders[last_reminder_key] = today
                        
                        logger.info(f"Deadline reminder sent for project {project.id}")
        except Exception as e:
            logger.error(f"Error in deadline reminder check: {str(e)}")


class EmmaServer:
    """Primary Object-Oriented Application Server wrapper"""
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.app = Flask(__name__)
        
        self.config = AppConfig()
        self.config.apply_to_app(self.app)

        # Map extensions
        db.init_app(self.app)
        self.mail = Mail(self.app)
        # Force long-polling only for Flask development server compatibility
        self.socketio = SocketIO(
            self.app, 
            cors_allowed_origins=self.config.allowed_origins, 
            ping_timeout=60, 
            ping_interval=25, 
            async_mode='threading',
            always_connect=False,
            engineio_logger=False,
            socketio_logger=False,
            transports=['polling']  # Disable WebSocket, use long-polling only
        )
        self.limiter = Limiter(
            app=self.app, key_func=get_remote_address, default_limits=["100000 per hour"], storage_uri="memory://"
        )

        # Configured limiters
        self.login_limiter = self.limiter.limit("5000 per minute")
        self.register_limiter = self.limiter.limit("5000 per minute")
        self.api_limiter = self.limiter.limit("1000000 per hour")
        self.admin_limiter = self.limiter.limit("200000 per hour")

        # Managers
        self.comms = CommunicationManager(self.app, self.mail, self.socketio, db, self.config)
        self.finance = FinanceManager(self.app, self.comms, db, self.config)
        self.scheduler = BackgroundScheduler()

        self._register_routes()
        self._register_sockets()
        self._setup_scheduler()
        
        self.app.after_request(self.after_request)

    def bind_route(self, rule, method_func, methods=None, limit=None, auth=None, admin=False, endpoint=None):
        """Elegant OOP Helper for stacking security routing protocols."""
        view = method_func
        if admin: view = SecurityManager.admin_required(view)
        if auth == 'login': view = SecurityManager.login_required(view)
        if limit: view = limit(view)
        
        if not hasattr(view, '__name__'):
            view.__name__ = method_func.__name__
            
        self.app.add_url_rule(rule, endpoint=endpoint or method_func.__name__, view_func=view, methods=methods or ["GET"])

    def is_loggedin(self):
        try:
          if session.get("user_id"):
            return jsonify({"status": "success"})
          else:
            return jsonify({"status": "notloggedin"})
        except Exception as e:
            self.logger.error(f"Couldn't verify login status: {str(e)}")
            db.session.rollback()
            return jsonify({"error": f"Couldn't verify login status: {str(e)}"}), 500

    def _register_routes(self):
        self.bind_route("/", self.dashboard, auth='login')
        self.bind_route("/login", self.login, methods=["GET", "POST"], limit=self.login_limiter)
        self.bind_route("/register", self.register, methods=["GET", "POST"], limit=self.register_limiter)
        self.bind_route("/logout", self.logout)
        self.bind_route("/forgot-password", self.request_password_reset, methods=["GET", "POST"], limit=self.login_limiter)
        self.bind_route("/reset-password/<token>", self.reset_password, methods=["GET", "POST"])
        
        self.bind_route("/invoices", self.invoices, auth='login', admin=True)
        self.bind_route("/client/notifications", self.client_notifications, auth='login')
        self.bind_route("/notifications", self.notifications, auth='login', admin=True)
        
        self.bind_route("/client/dashboard", self.client_portal, auth='login')
        self.bind_route("/client/register", self.client_register, auth='login')
        self.bind_route("/api/services", self.services_api, limit=self.api_limiter)
        self.bind_route("/services", self.services_page)
        self.bind_route("/client_billing", self.client_billing, auth='login')
        self.bind_route("/client/order", self.order_page, auth='login')
        self.bind_route("/client_feedback", self.client_feedback, auth='login')
        self.bind_route("/cookie-policy", self.cookie_policy)
        
        self.bind_route("/api/orders", self.place_order, methods=["POST"], auth='login')
        self.bind_route("/api/profile", self.get_profile)
        self.bind_route("/clients", self.clients_page, auth='login', admin=True)
        self.bind_route("/projects", self.projects_page, auth='login', admin=True)
        
        self.bind_route("/api/dashboard", self.dashboard_data, auth='login')
        self.bind_route("/api/clients", self.get_clients, auth='login', admin=True)
        self.bind_route("/api/test", self.test_connection)
        self.bind_route("/api/is_loggedin", self.is_loggedin, methods=["POST"])
        self.bind_route("/api/loggedin", self.is_loggedin, methods=["GET"])


        self.bind_route("/api/projects", self.get_projects, auth='login')
        self.bind_route("/api/projects", self.create_project, methods=["POST"], auth='login')
        self.bind_route("/api/projects/<int:project_id>", self.update_project, methods=["PATCH"], auth='login', admin=True)
        self.bind_route("/api/projects/<int:project_id>/payment", self.update_payment, methods=["POST"], auth='login', admin=True)
        self.bind_route("/api/projects/<int:project_id>", self.delete_project, methods=["DELETE"], auth='login', admin=True)
        
        self.bind_route("/api/payment/submit", self.submit_payment, methods=["POST"], auth='login')
        
        self.bind_route("/api/paypal/create-payment", self.paypal_create_payment, methods=["POST"], auth='login')
        self.bind_route("/api/paypal/execute-payment", self.paypal_execute_payment, methods=["GET", "POST"], auth='login')
        self.bind_route("/api/paypal/cancel-payment", self.paypal_cancel_payment)
        
        self.bind_route("/api/clients/add", self.admin_add_client_record, methods=["POST"], auth='login', admin=True)
        
        self.bind_route("/api/messages/<int:target_id>", self.api_messages, methods=["GET", "POST"], auth='login')
        self.bind_route("/api/feedback", self.api_feedback, methods=["GET", "POST"])
        
        self.bind_route("/api/messages/<int:message_id>/upload", self.upload_file, methods=["POST"], auth='login')
        self.bind_route("/api/files/<int:file_id>/download", self.download_file, auth='login')
        self.bind_route("/api/messages/<int:target_id>/files", self.get_message_files, auth='login')
        self.bind_route("/api/files/<int:file_id>", self.delete_file, methods=["DELETE"], auth='login')
        
        self.bind_route("/api/invoices", self.get_invoices, auth='login')
        self.bind_route("/api/invoices/<int:invoice_id>/pay", self.get_invoice_payment_link, auth='login')
        self.bind_route("/api/invoices/<int:invoice_id>/capture", self.capture_invoice_payment, methods=["POST"], auth='login')
        self.bind_route("/api/invoices/<int:invoice_id>/pdf", self.generate_invoice_pdf, auth='login')
        self.bind_route("/api/invoices/generate", self.api_generate_invoice, methods=["POST"], auth='login', admin=True)
        self.bind_route("/api/invoices/<int:invoice_id>/resend", self.api_resend_invoice_email, methods=["POST"], auth='login', admin=True)
        self.bind_route("/api/invoices/<int:invoice_id>/mark-paid", self.api_mark_invoice_paid, methods=["POST"], auth='login', admin=True)
        
        self.bind_route("/api/notifications", self.get_notifications, auth='login', limit=self.api_limiter)
        self.bind_route("/api/notifications/stats", self.get_notification_stats, auth='login', limit=self.api_limiter)
        self.bind_route("/api/notifications/<int:notification_id>/read", self.mark_notification_read, methods=["POST"], auth='login', limit=self.api_limiter)
        self.bind_route("/api/notifications/mark-all-read", self.mark_all_notifications_read, methods=["POST"], auth='login', limit=self.api_limiter)
        self.bind_route("/api/notifications/<int:notification_id>", self.delete_notification, methods=["DELETE"], auth='login', limit=self.api_limiter)
        self.bind_route("/api/notifications/delete-read", self.delete_read_notifications, methods=["DELETE"], auth='login', limit=self.api_limiter)
        
        self.bind_route("/api/admin/notifications", self.get_admin_notifications, auth='login', admin=True, limit=self.api_limiter)
        self.bind_route("/api/admin/notifications/stats", self.get_admin_notification_stats, auth='login', admin=True, limit=self.api_limiter)
        self.bind_route("/api/admin/notifications/<int:notification_id>/read", self.mark_admin_notification_read, methods=["POST"], auth='login', admin=True, limit=self.api_limiter)
        self.bind_route("/api/admin/notifications/mark-all-read", self.mark_all_admin_notifications_read, methods=["POST"], auth='login', admin=True, limit=self.api_limiter)
        self.bind_route("/api/admin/notifications/<int:notification_id>", self.delete_admin_notification, methods=["DELETE"], auth='login', admin=True, limit=self.api_limiter)
        self.bind_route("/api/admin/notifications/delete-read", self.delete_read_admin_notifications, methods=["DELETE"], auth='login', admin=True, limit=self.api_limiter)
        
        self.bind_route("/api/client/notifications", self.get_client_notifications, auth='login', limit=self.api_limiter)
        self.bind_route("/api/client/notifications/stats", self.get_client_notification_stats, auth='login', limit=self.api_limiter)
        self.bind_route("/api/client/notifications/<int:notification_id>/read", self.mark_client_notification_read, methods=["POST"], auth='login', limit=self.api_limiter)
        self.bind_route("/api/client/notifications/mark-all-read", self.mark_all_client_notifications_read, methods=["POST"], auth='login', limit=self.api_limiter)
        self.bind_route("/api/client/notifications/<int:notification_id>", self.delete_client_notification, methods=["DELETE"], auth='login', limit=self.api_limiter)
        self.bind_route("/api/client/notifications/delete-read", self.delete_read_client_notifications, methods=["DELETE"], auth='login', limit=self.api_limiter)

    def _register_sockets(self):
        self.socketio.on('connect')(self.handle_connect)
        self.socketio.on('disconnect')(self.handle_disconnect)
        self.socketio.on('mark_notification_read')(self.handle_mark_read)
        self.socketio.on('get_notifications')(self.handle_get_notifications)

    def _setup_scheduler(self):
        self.scheduler.add_job(
            func=self.finance.check_invoice_reminders,
            trigger="interval", hours=1, id='invoice_reminder_check',
            name='Check invoice payment reminders', replace_existing=True
        )
        self.scheduler.add_job(
            func=self.finance.check_deadline_reminders,
            trigger="interval", hours=6, id='deadline_reminder_check',
            name='Check project deadline reminders', replace_existing=True
        )
        self.scheduler.add_job(
            func=self.cleanup_old_notifications,
            trigger="interval", hours=24, id='notification_cleanup',
            name='Clean up old notifications', replace_existing=True
        )
        self.scheduler.add_job(
            func=self.cleanup_expired_reset_tokens,
            trigger="interval", hours=6, id='reset_token_cleanup',
            name='Clean up expired password reset tokens', replace_existing=True
        )
        try:
            self.scheduler.start()
            self.logger.info("Scheduler started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start scheduler: {str(e)}")

    def after_request(self, response):
        origin = request.headers.get('Origin')
        if origin in self.config.allowed_origins or '*' in self.config.allowed_origins:
            response.headers.add('Access-Control-Allow-Origin', origin if origin else '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    def cleanup_old_notifications(self):
        try:
            with self.app.app_context():
                cleanup_days = int(os.environ.get('NOTIFICATION_CLEANUP_DAYS', '90'))
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=cleanup_days)

                deleted_count = Notification.query.filter(
                    Notification.created_at < cutoff_date,
                    Notification.read == True
                ).delete()

                if deleted_count > 0:
                    db.session.commit()
                    logger.info(f"Cleaned up {deleted_count} old read notifications older than {cleanup_days} days")
        except Exception as e:
            logger.error(f"Error in notification cleanup: {str(e)}")

    def cleanup_expired_reset_tokens(self):
        """Clean up expired and used password reset tokens"""
        try:
            with self.app.app_context():
                # Delete tokens that are expired or already used
                deleted_count = PasswordResetToken.query.filter(
                    (PasswordResetToken.expires_at < datetime.now(timezone.utc)) |
                    (PasswordResetToken.used == True)
                ).delete()

                if deleted_count > 0:
                    db.session.commit()
                    logger.info(f"Cleaned up {deleted_count} expired/used password reset tokens")
        except Exception as e:
            logger.error(f"Error in password reset token cleanup: {str(e)}")

    # --- View Routings ---
    def dashboard(self):
        if session.get("role", "client").lower() == "admin":
            users = User.query.all()
            clients = [u for u in users if (u.role or "").lower() == "client"]
            return render_template("index.html", clients=len(clients), projects=Project.query.count())
        return redirect(url_for("client_portal"))

    def login(self):
        if request.method == "GET": return render_template("login.html")
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not password: return render_template("login.html", error="Username and password are required")
        if not SecurityManager.validate_username(username): return render_template("login.html", error="Invalid username format")
        
        user = User.query.filter_by(username=username).first()
        dummy_hash = "$2b$12$Z0bT5.YfD98O47M6jIqR9unbKkX3iB/Yt/Yh35Xq.RzR9M/Yt/Yh3"
        if not user or not user.password:
            bcrypt.checkpw(password.encode('utf-8'), dummy_hash.encode('utf-8'))
            return render_template("login.html", error="Invalid credentials")
        if not SecurityManager.verify_password(password, user.password):
            return render_template("login.html", error="Invalid credentials")
            
        session.clear()
        session["user"] = user.username
        session["user_id"] = user.id
        session["role"] = user.role or "client"
        session.permanent = True
        return redirect(url_for("dashboard"))

    def register(self):
        if request.method == "GET": return render_template("login.html", register=True)
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        email = request.form.get("email", "").strip()
        
        if not username or not password or not email: return render_template("login.html", register=True, error="Required fields missing")
        if not SecurityManager.validate_username(username): return render_template("login.html", register=True, error="Invalid username format")
        
        valid, msg = SecurityManager.validate_password(password)
        if not valid: return render_template("login.html", register=True, error=msg)
        
        if User.query.filter(db.func.lower(User.username) == username.lower()).first():
            return render_template("login.html", register=True, error="User already exists")
            
        role = "admin" if User.query.count() == 0 else "client"
        new_user = User(username=username, password=SecurityManager.hash_password(password), email=email, role=role, date_added=date.today())
        db.session.add(new_user)
        db.session.commit()
        
        session.clear()
        session["user"] = new_user.username
        session["user_id"] = new_user.id
        session["role"] = new_user.role
        session.permanent = True
        
        for admin in User.query.filter_by(role="admin").all():
            self.comms.send_notification(admin.id, "registration", "New Client Registration", f"New client '{username}' has registered.", {"client_id": new_user.id})
        if role == "admin":
            return redirect(url_for("dashboard"))
        return redirect(url_for("client_register"))


    def logout(self):
        session.clear()
        return redirect(url_for("login"))

    def request_password_reset(self):
        """Handle password reset request - send email with reset link"""
        if request.method == "GET":
            return render_template("forgot_password.html")

        email = request.form.get("email", "").strip()
        if not email:
            return render_template("forgot_password.html", error="Email is required")
        if not SecurityManager.validate_email(email):
            return render_template("forgot_password.html", error="Invalid email format")

        user = User.query.filter_by(email=email).first()
        if not user:
            # Don't reveal if email exists for security
            return render_template("forgot_password.html", success="If an account with this email exists, a reset link has been sent.")

        # Generate reset token
        token = SecurityManager.generate_reset_token()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

        # Invalidate any existing tokens for this user
        PasswordResetToken.query.filter_by(user_id=user.id).delete()

        # Create new token
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=expires_at
        )
        db.session.add(reset_token)
        db.session.commit()

        # Send reset email
        try:
            self.comms.send_password_reset_email(user.email, token)
            return render_template("forgot_password.html", success="If an account with this email exists, a reset link has been sent.")
        except Exception as e:
            logger.error(f"Error sending password reset email: {str(e)}")
            return render_template("forgot_password.html", error="Error sending reset email. Please try again.")

    def reset_password(self, token):
        """Handle password reset with token"""
        if request.method == "GET":
            # Validate token
            is_valid, error_msg = SecurityManager.validate_reset_token(token)
            if not is_valid:
                return render_template("reset_password.html", error=error_msg, token=token)

            reset_token = PasswordResetToken.query.filter_by(token=token).first()
            if not reset_token:
                return render_template("reset_password.html", error="Invalid or expired reset link", token=token)

            if reset_token.used:
                return render_template("reset_password.html", error="This reset link has already been used", token=token)

            # Handle timezone-aware/naive datetime comparison
            expires_at = reset_token.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            if expires_at < datetime.now(timezone.utc):
                return render_template("reset_password.html", error="Reset link has expired", token=token)

            return render_template("reset_password.html", token=token)

        # POST - handle password reset
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not password or not confirm_password:
            return render_template("reset_password.html", error="Password fields are required", token=token)

        if password != confirm_password:
            return render_template("reset_password.html", error="Passwords do not match", token=token)

        valid, msg = SecurityManager.validate_password(password)
        if not valid:
            return render_template("reset_password.html", error=msg, token=token)

        # Validate token again
        reset_token = PasswordResetToken.query.filter_by(token=token).first()
        
        # Handle timezone-aware/naive datetime comparison
        expires_at = reset_token.expires_at if reset_token else None
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if not reset_token or reset_token.used or (expires_at and expires_at < datetime.now(timezone.utc)):
            return render_template("reset_password.html", error="Invalid or expired reset link", token=token)

        # Update password
        user = User.query.get(reset_token.user_id)
        if not user:
            return render_template("reset_password.html", error="User not found", token=token)

        user.password = SecurityManager.hash_password(password)
        reset_token.used = True
        db.session.commit()

        logger.info(f"Password reset successfully for user {user.username}")
        return redirect(url_for('login', success="Password has been reset successfully. Please login with your new password."))

    def invoices(self): return render_template("invoices.html")
    def client_notifications(self): return render_template("client_notification.html")
    def notifications(self): return render_template("notifications.html")
    def client_portal(self): return render_template("client_portal.html")
    def client_register(self): return render_template("client_register.html")
    def services_api(self): return jsonify([{"id": s.id, "name": s.name, "description": s.description, "price": s.price, "icon": s.icon} for s in Service.query.all()])
    def services_page(self): return render_template("services.html", services=Service.query.all())
    def client_billing(self): return render_template("client_billing.html")
    def order_page(self): return render_template("client_order.html")
    def client_feedback(self): return render_template("client_feedback.html")
    def cookie_policy(self): return render_template("cookie_policy.html")
    def get_profile(self): return jsonify({"name": "Emmanuel Ugwu", "headline": "Expert Freelance Software Developer", "services": [{"name": "Application Development"}]})
    def clients_page(self): return render_template("clients.html")
    def projects_page(self): return render_template("projects.html")

    def dashboard_data(self):
        uid = session.get("user_id")
        projects = Project.query.all() if session.get("role", "client").lower() == "admin" else Project.query.filter_by(client_user_id=uid).all()
        status_counts = {}
        total_rev, total_paid = 0.0, 0.0
        for p in projects:
            st = p.status or "Pending"
            status_counts[st] = status_counts.get(st, 0) + 1
            total_rev += float(p.price or 0)
            total_paid += float(p.amount_paid or 0)
        return jsonify({"status_counts": status_counts, "total_revenue": total_rev, "total_paid": total_paid})

    def get_clients(self):
        return jsonify([{"id": c.id, "username": c.username, "email": c.email, "company": c.company, "role": c.role, "type": c.type, "date_added": c.date_added.isoformat() if c.date_added else None} for c in User.query.filter_by(role="client").all()])

    def test_connection(self):
        return jsonify({"status": "success", "database_connected": True, "projects_count": Project.query.count(), "users_count": User.query.count(), "session": {"user": session.get("user"), "logged_in": session.get("user_id") is not None}})

    def place_order(self):
        if request.content_type and 'multipart/form-data' in request.content_type:
            service_name = SecurityManager.sanitize_input(request.form.get("service_name", ""))
            description = SecurityManager.sanitize_input(request.form.get("description", ""))
            budget = SecurityManager.sanitize_input(request.form.get("budget", ""))
            deadline_str = SecurityManager.sanitize_input(request.form.get("deadline", ""))
            price_str = request.form.get("price", "0")
            uploaded_files = request.files.getlist('files')
        else:
            data = request.json or {}
            service_name = SecurityManager.sanitize_input(data.get("service_name", ""))
            description = SecurityManager.sanitize_input(data.get("description", ""))
            budget = SecurityManager.sanitize_input(data.get("budget", ""))
            deadline_str = SecurityManager.sanitize_input(data.get("deadline", ""))
            price_str = data.get("price", "0")
            uploaded_files = []
        
        try: price = float(price_str)
        except: return jsonify({"error": "Invalid price format"}), 400

        if not service_name or len(service_name) > 255: return jsonify({"error": "Invalid service name"}), 400

        # Validate deadline if provided
        deadline = None
        if deadline_str:
            try:
                deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
                today = date.today()
                min_date = today + timedelta(days=3)
                
                if deadline < min_date:
                    return jsonify({"error": "Deadline must be at least 3 days from today"}), 400
            except ValueError:
                return jsonify({"error": "Invalid deadline format"}), 400

        current_user_id = session.get("user_id")
        current_username = session.get("user", "Guest")
        new_project = Project(client_user_id=current_user_id, client_name=current_username, title=service_name, desc=description, budget_estimate=budget, price=price, deadline=deadline)
        db.session.add(new_project)
        db.session.flush()

        # Include deadline in notification if provided
        deadline_info = f" | Deadline: {deadline.strftime('%B %d, %Y')}" if deadline else ""
        msg = Message(client_id=current_user_id, from_role="client", content=f"💼 NEW ORDER: Client '{current_username}' placed order for '{service_name}' | Est. Price: £{price:.2f}{deadline_info}")
        db.session.add(msg)
        db.session.flush()

        for file in uploaded_files:
            if file and file.filename and SecurityManager.allowed_file(file.filename):
                original_filename = secure_filename(file.filename)
                stored_filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}_{original_filename}"
                file_path = self.config.UPLOADS_DIR / stored_filename
                try:
                    file.save(str(file_path))
                    attachment = FileAttachment(message_id=msg.id, client_id=current_user_id, original_filename=original_filename, stored_filename=stored_filename, file_size=file.content_length, mime_type=file.content_type, uploaded_by_role="client")
                    db.session.add(attachment)
                except Exception as e:
                    self.logger.error(f"Failed to save file: {str(e)}")

        db.session.commit()
        return jsonify({"status": "success", "message": "Order transmitted successfully."})

    def get_projects(self):
        role = session.get("role", "client")
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        query = Project.query.order_by(Project.date_created.desc()) if role.lower() == "admin" else Project.query.filter_by(client_user_id=session.get("user_id")).order_by(Project.date_created.desc())
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        projects_data = []
        for p in paginated.items:
            client_details = None
            if p.client_user_id:
                client = db.session.get(User, p.client_user_id)
                if client: 
                    client_details = {"username": client.username, "email": client.email, "company": client.company, "date_added": client.date_added.isoformat() if client.date_added else None}
            
            attached_files = []
            if p.client_user_id:
                # Get all messages with attachments for this client, ordered by timestamp
                order_messages = Message.query.filter_by(client_id=p.client_user_id).filter(Message.attachments.any()).order_by(Message.timestamp.desc()).all()
                # Get the most recent message with attachments for this project
                if order_messages:
                    attached_files = [{"id": f.id, "original_filename": f.original_filename, "file_size": f.file_size, "download_url": f"/api/files/{f.id}/download"} for f in order_messages[0].attachments]

            project_data = {
                "id": p.id, "client_user_id": p.client_user_id, "client_name": p.client_name or (db.session.get(User, p.client_user_id).username if db.session.get(User, p.client_user_id) else None),
                "client_details": client_details, "title": p.title, "desc": p.desc, "status": p.status, "date_created": p.date_created.isoformat() if p.date_created else None,
                "amount_paid": float(p.amount_paid or 0), "price": float(p.price or 0), "attached_files": attached_files
            }
            if p.deadline:
                delta = p.deadline - date.today()
                project_data.update({"deadline": p.deadline.isoformat(), "days_until_deadline": delta.days, "deadline_status": "overdue" if delta.days < 0 else "urgent" if delta.days <= 3 else "normal"})
            projects_data.append(project_data)

        return jsonify({"data": projects_data, "pagination": {"page": page, "per_page": per_page, "total": paginated.total, "pages": paginated.pages}})

    def create_project(self):
        data = request.json or {}
        title = SecurityManager.sanitize_input(data.get("title", ""))
        if not SecurityManager.validate_project_title(title): return jsonify({"error": "Invalid title"}), 400
        
        client_id = data.get("client_user_id") if session.get("role", "client").lower() == "admin" else session.get("user_id")
        client_name = db.session.get(User, client_id).username if session.get("role", "client").lower() == "admin" else session.get("user")
        
        try: price = float(data.get("price", 0.0))
        except: return jsonify({"error": "Invalid price format"}), 400
        
        new_project = Project(client_user_id=client_id, client_name=client_name, title=title, desc=SecurityManager.sanitize_input(data.get("desc", "")), budget_estimate=SecurityManager.sanitize_input(data.get("budget_estimate", "")), price=price)
        db.session.add(new_project)
        db.session.commit()
        
        self.comms.send_notification(client_id, "project_status", "New Project Created", f"Your project '{title}' has been created.", {"project_id": new_project.id})
        return jsonify({"status": "success", "project": {"id": new_project.id, "title": new_project.title}})

    def update_project(self, project_id):
        project = db.session.get(Project, project_id)
        if not project: return jsonify({"error": "Project not found"}), 404
        data = request.json or {}
        if "status" in data:
            old_status = project.status
            project.status = SecurityManager.sanitize_input(data["status"])
            if old_status != project.status:
                self.comms.send_notification(project.client_user_id, "project_status", "Project Status Updated", f"Status updated to '{project.status}'.", {"project_id": project.id})
                if project.status.lower() == "completed": self.finance.generate_invoice(project.id, "completion")
        if "amount_paid" in data:
            try: project.amount_paid = float(data["amount_paid"])
            except: return jsonify({"error": "Invalid amount"}), 400
        db.session.commit()
        return jsonify({"status": "success"})

    def update_payment(self, project_id):
        try: amount = float((request.json or {}).get("amount", 0))
        except: return jsonify({"error": "Invalid amount"}), 400
        project = db.session.get(Project, project_id)
        if not project: return jsonify({"error": "Project not found"}), 404
        project.amount_paid = float(project.amount_paid or 0) + amount
        db.session.commit()
        return jsonify({"status": "success"})

    def delete_project(self, project_id):
        project = db.session.get(Project, project_id)
        if not project: return jsonify({"error": "Project not found"}), 404
        db.session.delete(project)
        db.session.commit()
        return jsonify({"status": "success"})

    def submit_payment(self):
        data = request.json or {}
        try: amount = float(data.get("amount")); project_id = int(data.get("project_id"))
        except: return jsonify({"error": "Invalid amount"}), 400
        project = db.session.get(Project, project_id)
        if not project or (session.get("role").lower() != "admin" and project.client_user_id != session.get("user_id")): return jsonify({"error": "Access denied"}), 403
        
        project.amount_paid = float(project.amount_paid or 0) + amount
        db.session.add(Message(client_id=project.client_user_id, from_role="client", content=f"💳 PAYMENT SENT: £{amount:.2f} via {SecurityManager.sanitize_input(data.get('payment_method', 'Bank'))}"))
        db.session.commit()
        return jsonify({"status": "success"})

    def paypal_create_payment(self):
        data = request.json or {}
        try: amount = float(data.get("amount")); project_id = int(data.get("project_id"))
        except: return jsonify({"error": "Invalid payload"}), 400
        project = db.session.get(Project, project_id)
        if not project or (session.get("role").lower() != "admin" and project.client_user_id != session.get("user_id")): return jsonify({"error": "Access denied"}), 403
        
        token = self.finance.get_paypal_access_token()
        if not token: return jsonify({"error": "PayPal Auth Failed"}), 500
        payload = {"intent": "sale", "payer": {"payment_method": "paypal"}, "redirect_urls": {"return_url": url_for("paypal_execute_payment", _external=True), "cancel_url": url_for("paypal_cancel_payment", _external=True)}, "transactions": [{"amount": {"total": str(round(amount, 2)), "currency": "GBP"}, "description": f"Payment for {project.title}", "custom": str(project_id)}]}
        res = requests.post(f"{self.config.PAYPAL_API_BASE}/v1/payments/payment", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=payload)
        if res.status_code == 201:
            payment_id = res.json().get("id")
            session[f"paypal_payment_{project_id}"] = payment_id
            return jsonify({"status": "success", "payment_id": payment_id, "approval_url": next(link.get("href") for link in res.json().get("links", []) if link.get("rel") == "approval_url")})
        return jsonify({"error": "PayPal API Error"}), 400

    def paypal_execute_payment(self):
        payment_id = request.args.get("paymentId")
        payer_id = request.args.get("PayerID")
        token = self.finance.get_paypal_access_token()
        res = requests.post(f"{self.config.PAYPAL_API_BASE}/v1/payments/payment/{payment_id}/execute", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json={"payer_id": payer_id})
        
        if res.status_code == 200:
            custom = res.json().get("transactions", [])[0].get("custom")
            amount = float(res.json().get("transactions", [])[0].get("amount", {}).get("total", 0))
            project = Project.query.get(int(custom))
            project.amount_paid = float(project.amount_paid or 0) + amount
            db.session.add(Message(client_id=project.client_user_id, from_role="client", content=f"💳 PAYMENT RECEIVED: £{amount:.2f} via PayPal."))
            db.session.commit()
            return jsonify({"status": "success"})
        return jsonify({"error": "Execution Failed"}), 400

    def paypal_cancel_payment(self): return jsonify({"status": "cancelled"})

    def admin_add_client_record(self):
        data = request.json or {}
        username = SecurityManager.sanitize_input(data.get("username", ""))
        if not SecurityManager.validate_username(username) or User.query.filter(db.func.lower(User.username) == username.lower()).first(): return jsonify({"error": "Invalid or existing username"}), 400
        new_user = User(username=username, email=SecurityManager.sanitize_input(data.get("email", "N/A")), role=SecurityManager.sanitize_input(data.get("role", "Client")).lower(), type="record_only", date_added=date.today())
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"status": "success"})

    def api_messages(self, target_id):
        uid = session.get("user_id")
        if session.get("role").lower() != "admin":
            if target_id != 0 and target_id != uid: return jsonify({"error": "Access denied"}), 403
            target_id = uid
        if request.method == "GET":
            return jsonify([{"id": m.id, "client_id": m.client_id, "from_role": m.from_role, "content": m.content, "timestamp": m.timestamp.isoformat(), "attachments": [{"id": a.id, "original_filename": a.original_filename, "file_size": a.file_size, "download_url": f"/api/files/{a.id}/download"} for a in m.attachments]} for m in Message.query.filter_by(client_id=target_id).order_by(Message.timestamp.asc()).all()])
        try:
            content = SecurityManager.sanitize_input((request.form if request.content_type and 'multipart/form-data' in request.content_type else request.json).get("content", ""))
            if not content: return jsonify({"error": "No content"}), 400
            msg = Message(client_id=target_id, from_role="admin" if session.get("role").lower() == "admin" else "client", content=content)
            db.session.add(msg)
            db.session.flush()

            uploaded_files = []
            for file in request.files.getlist('files') if request.content_type and 'multipart/form-data' in request.content_type else []:
                if file and SecurityManager.allowed_file(file.filename):
                    sf = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}_{secure_filename(file.filename)}"
                    try:
                        file.save(str(self.config.UPLOADS_DIR / sf))
                        db.session.add(FileAttachment(message_id=msg.id, client_id=target_id, original_filename=secure_filename(file.filename), stored_filename=sf, file_size=file.content_length, mime_type=file.content_type, uploaded_by_role=msg.from_role))
                        uploaded_files.append(secure_filename(file.filename))
                    except Exception as e:
                        self.logger.error(f"Failed to save file: {str(e)}")
            
            db.session.commit()
            
            # Only send notification to the recipient, not the sender
            if session.get("role").lower() == "admin":
                # Admin sending to client - notify the client
                self.comms.send_notification(target_id, "message", "New Message", f"New message from {session.get('user')}", {"message_id": msg.id})
            # Client sending message - no notification needed for sender
            
            # Send file upload notifications for each successfully uploaded file
            for filename in uploaded_files:
                if session.get("role").lower() == "admin":
                    # Admin uploading file - notify the client
                    self.comms.send_notification(target_id, "file_upload", "File Uploaded", f"File '{filename}' was uploaded", {"message_id": msg.id, "filename": filename})
            
            return jsonify({"status": "success", "message": {"id": msg.id, "content": msg.content}})
        except Exception as e:
            self.logger.error(f"Message creation failed: {str(e)}")
            db.session.rollback()
            return jsonify({"error": f"Message creation failed: {str(e)}"}), 500

    def api_feedback(self):
        if request.method == "GET": return jsonify({"data": [{"client_name": f.client_name, "rating": f.rating, "comment": f.comment, "created_at": f.created_at.isoformat()} for f in Feedback.query.order_by(Feedback.created_at.desc()).all()]})
        data = request.json or {}
        feedback = Feedback(client_name=SecurityManager.sanitize_input(data.get("clientName")), service_category=SecurityManager.sanitize_input(data.get("serviceCategory")), rating=int(data.get("rating")), comment=SecurityManager.sanitize_input(data.get("comment")))
        db.session.add(feedback)
        db.session.commit()
        return jsonify({"status": "success"})

    def upload_file(self, message_id):
        msg = db.session.get(Message, message_id)
        if not msg or (session.get("role").lower() != "admin" and msg.client_id != session.get("user_id")): return jsonify({"error": "Access denied"}), 403
        file = request.files.get('file')
        if not file or not SecurityManager.allowed_file(file.filename): return jsonify({"error": "Invalid file"}), 400
        
        sf = f"{secrets.token_hex(16)}_{secure_filename(file.filename)}"
        file_path = SecurityManager.get_safe_file_path(sf, self.config.UPLOADS_DIR)
        
        try:
            file.save(str(file_path))
            attachment = FileAttachment(message_id=message_id, client_id=msg.client_id, original_filename=secure_filename(file.filename), stored_filename=sf, file_size=file.content_length, mime_type=file.content_type, uploaded_by_role="admin" if session.get("role").lower() == "admin" else "client")
            db.session.add(attachment)
            db.session.commit()
            return jsonify({"status": "success", "attachment": {"id": attachment.id, "original_filename": attachment.original_filename, "file_size": attachment.file_size, "download_url": f"/api/files/{attachment.id}/download"}})
        except Exception as e:
            self.logger.error(f"File upload failed: {str(e)}")
            db.session.rollback()
            return jsonify({"error": f"File upload failed: {str(e)}"}), 500

    def download_file(self, file_id):
        try:
            attachment = db.session.get(FileAttachment, file_id)
            if not attachment:
                logger.error(f"File attachment {file_id} not found in database")
                return jsonify({"error": "File not found"}), 404
            
            if session.get("role").lower() != "admin" and attachment.client_id != session.get("user_id"):
                warning_msg = f"Access denied for file {file_id} by user {session.get('user_id')} (role: {session.get('role')})"
                logger.warning(warning_msg)
                return jsonify({"error": "Access denied"}), 403
            
            file_path = SecurityManager.get_safe_file_path(attachment.stored_filename, self.config.UPLOADS_DIR)
            
            if not file_path.exists():
                logger.error(f"File not found on disk: {file_path} (stored_filename: {attachment.stored_filename})")
                return jsonify({"error": "File not found on server"}), 404
            
            logger.info(f"Downloading file {file_id}: {attachment.original_filename} from {file_path}")
            return send_file(file_path, as_attachment=True, download_name=attachment.original_filename)
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {str(e)}")
            return jsonify({"error": "Download failed"}), 500

    def get_message_files(self, target_id):
        target_id = session.get("user_id") if session.get("role").lower() != "admin" and target_id == 0 else target_id
        return jsonify({"files": [{"id": f.id, "message_id": f.message_id, "original_filename": f.original_filename, "file_size": f.file_size} for f in FileAttachment.query.filter_by(client_id=target_id).all()]})

    def delete_file(self, file_id):
        attachment = db.session.get(FileAttachment, file_id)
        if not attachment or (session.get("role").lower() != "admin" and attachment.client_id != session.get("user_id")): return jsonify({"error": "Denied"}), 403
        filepath = SecurityManager.get_safe_file_path(attachment.stored_filename, self.config.UPLOADS_DIR)
        if filepath.exists(): filepath.unlink()
        db.session.delete(attachment)
        db.session.commit()
        return jsonify({"status": "success"})

    # Invoices & Notifications standard mappings
    def get_invoices(self):
        try:
            user_role = session.get("role", "client").lower()
            user_id = session.get("user_id")
            
            # Admin sees all invoices, clients see only their own
            if user_role == "admin":
                invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
            else:
                invoices = Invoice.query.filter_by(client_id=user_id).order_by(Invoice.created_at.desc()).all()
            
            return jsonify({
                "invoices": [
                    {
                        "id": i.id,
                        "invoice_number": i.invoice_number,
                        "status": i.status,
                        "amount": i.amount,
                        "due_date": i.due_date.isoformat() if i.due_date else None,
                        "invoice_type": i.invoice_type,
                        "project_id": i.project_id,
                        "client_id": i.client_id,
                        "project_title": i.project.title if i.project else None,
                        "client_name": i.client.username if i.client else None,
                        "client_email": i.client.email if i.client else None,
                        "project_price": float(i.project.price) if i.project and i.project.price else 0.0,
                        "amount_paid": float(i.project.amount_paid) if i.project and i.project.amount_paid else 0.0,
                        "balance": float(i.project.price - i.project.amount_paid) if i.project and i.project.price else 0.0,
                        "created_at": i.created_at.isoformat() if i.created_at else None,
                        "paid_at": i.paid_at.isoformat() if i.paid_at else None,
                        "is_overdue": i.due_date and i.due_date < date.today() and i.status != 'paid'
                    } for i in invoices
                ]
            })
        except Exception as e:
            logger.error(f"Error fetching invoices: {str(e)}")
            return jsonify({"error": "Failed to fetch invoices"}), 500

    def get_invoice_payment_link(self, invoice_id):
        try:
            invoice = db.session.get(Invoice, invoice_id)
            if not invoice:
                return jsonify({"error": "Invoice not found"}), 404
            if invoice.status == 'paid':
                return jsonify({"error": "Invoice already paid"}), 400
            
            token = self.finance.get_paypal_access_token()
            if not token:
                return jsonify({"error": "PayPal authentication failed"}), 500
            
            payload = {
                "intent": "sale",
                "payer": {"payment_method": "paypal"},
                "redirect_urls": {
                    "return_url": url_for("paypal_execute_payment", _external=True),
                    "cancel_url": url_for("paypal_cancel_payment", _external=True)
                },
                "transactions": [{
                    "amount": {"total": str(round(invoice.amount, 2)), "currency": "GBP"},
                    "description": f"Invoice {invoice.invoice_number} - {invoice.invoice_type}",
                    "custom": f"invoice_{invoice.id}"
                }]
            }
            
            res = requests.post(
                f"{self.config.PAYPAL_API_BASE}/v1/payments/payment",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload
            )
            
            if res.status_code == 201:
                payment_id = res.json().get("id")
                session[f"paypal_invoice_{invoice_id}"] = payment_id
                approval_url = next(link.get("href") for link in res.json().get("links", []) if link.get("rel") == "approval_url")
                return jsonify({"status": "success", "payment_id": payment_id, "approval_url": approval_url})
            
            return jsonify({"error": "PayPal API error"}), 400
        except Exception as e:
            logger.error(f"Error getting invoice payment link: {str(e)}")
            return jsonify({"error": "Failed to generate payment link"}), 500

    def capture_invoice_payment(self, invoice_id):
        try:
            invoice = db.session.get(Invoice, invoice_id)
            if not invoice:
                return jsonify({"error": "Invoice not found"}), 404
            
            invoice.status = 'paid'
            invoice.paid_at = datetime.now(timezone.utc)
            
            if invoice.project:
                invoice.project.amount_paid = float(invoice.project.amount_paid or 0) + invoice.amount
            
            db.session.commit()
            
            self.comms.send_notification(
                user_id=invoice.client_id,
                notification_type="payment",
                title="Payment Received",
                message=f"Invoice {invoice.invoice_number} has been marked as paid.",
                data={"invoice_id": invoice.id, "amount": invoice.amount}
            )
            
            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Error capturing invoice payment: {str(e)}")
            db.session.rollback()
            return jsonify({"error": "Failed to capture payment"}), 500

    def generate_invoice_pdf(self, invoice_id):
        try:
            invoice = db.session.get(Invoice, invoice_id)
            if not invoice:
                return jsonify({"error": "Invoice not found"}), 404
            
            project = invoice.project
            client = invoice.client
            
            if not project or not client:
                return jsonify({"error": "Missing project or client data"}), 400
            
            cache_path = self.finance.get_pdf_cache_path(invoice_id)
            
            if self.finance.is_pdf_cached(invoice_id):
                logger.info(f"Returning cached PDF for invoice {invoice_id}")
                return send_file(
                    cache_path,
                    as_attachment=True,
                    download_name=f"Invoice: {invoice.invoice_number.title()} {project.title} for {client.username}.pdf",
                    mimetype='application/pdf'
                )
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch, leftMargin=0.75*inch, rightMargin=0.75*inch)
            styles = getSampleStyleSheet()
            story = []
            
            invoice_type = invoice.invoice_type.lower()
            
            if invoice_type == 'milestone':
                title_color = colors.HexColor('#0a192f')
                header_color = colors.HexColor('#00f2fe')
                title_text = "MILESTONE INVOICE"
            elif invoice_type == 'completion':
                title_color = colors.HexColor('#1a365d')
                header_color = colors.HexColor('#38b2ac')
                title_text = "COMPLETION INVOICE"
            else:
                title_color = colors.HexColor('#0a192f')
                header_color = colors.HexColor('#00f2fe')
                title_text = "INVOICE"
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=title_color,
                spaceAfter=30,
                alignment=1
            )
            
            header_style = ParagraphStyle(
                'CustomHeader',
                parent=styles['Heading2'],
                fontSize=16,
                textColor=header_color,
                spaceAfter=12,
                spaceBefore=20
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=11,
                textColor=colors.HexColor('#333333'),
                spaceAfter=8
            )
            
            bold_style = ParagraphStyle(
                'CustomBold',
                parent=styles['Normal'],
                fontSize=11,
                textColor=colors.HexColor('#00ff00'),
                fontName='Helvetica-Bold',
                spaceAfter=8
            )
            
            story.append(Paragraph(title_text, title_style))
            story.append(Spacer(1, 0.2*inch))
            
            header_data = [
                [Paragraph("<b>Invoice Number:</b>", bold_style), Paragraph(invoice.invoice_number, normal_style)],
                [Paragraph("<b>Date Issued:</b>", bold_style), Paragraph(invoice.created_at.strftime('%B %d, %Y'), normal_style)],
                [Paragraph("<b>Due Date:</b>", bold_style), Paragraph(invoice.due_date.strftime('%B %d, %Y'), normal_style)],
                [Paragraph("<b>Status:</b>", bold_style), Paragraph(invoice.status.upper(), normal_style)],
            ]
            
            header_table = Table(header_data, colWidths=[2*inch, 3*inch], hAlign='LEFT')
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ]))
            story.append(header_table)
            story.append(Spacer(1, 0.3*inch))
            
            story.append(Paragraph("BILL TO", header_style))
            
            client_data = [
                [Paragraph("<b>Client:</b>", bold_style), Paragraph(client.username, normal_style)],
                [Paragraph("<b>Email:</b>", bold_style), Paragraph(client.email or 'N/A', normal_style)],
                [Paragraph("<b>Company:</b>", bold_style), Paragraph(client.company or 'Not indicated', normal_style)],
            ]
            
            if client.address:
                client_data.append([Paragraph("<b>Address:</b>", bold_style), Paragraph(client.address, normal_style)])
            if client.city:
                client_data.append([Paragraph("<b>City:</b>", bold_style), Paragraph(client.city, normal_style)])
            if client.country:
                client_data.append([Paragraph("<b>Country:</b>", bold_style), Paragraph(client.country, normal_style)])
            
            client_table = Table(client_data, colWidths=[2*inch, 4*inch], hAlign='LEFT')
            client_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ]))
            story.append(client_table)
            story.append(Spacer(1, 0.3*inch))
            
            story.append(Paragraph("PROJECT DETAILS", header_style))
            
            project_data = [
                [Paragraph("<b>Project:</b>", bold_style), Paragraph(project.title, normal_style)],
                [Paragraph("<b>Description:</b>", bold_style), Paragraph(project.desc or 'N/A', normal_style)],
                [Paragraph("<b>Invoice Type:</b>", bold_style), Paragraph(invoice.invoice_type.title(), normal_style)],
            ]
            
            if invoice_type == 'milestone':
                project_data.append([Paragraph("<b>Progress:</b>", bold_style), Paragraph("50% Complete", normal_style)])
            elif invoice_type == 'completion':
                project_data.append([Paragraph("<b>Progress:</b>", bold_style), Paragraph("100% Complete", normal_style)])
            
            project_table = Table(project_data, colWidths=[2*inch, 4*inch], hAlign='LEFT')
            project_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ]))
            story.append(project_table)
            story.append(Spacer(1, 0.3*inch))
            
            story.append(Paragraph("INVOICE ITEMS", header_style))
            
            items_data = [[Paragraph("<b>Description</b>", bold_style), Paragraph("<b>Quantity</b>", bold_style), Paragraph("<b>Price</b>", bold_style), Paragraph("<b>Total</b>", bold_style)]]
            
            if invoice.items:
                for item in invoice.items:
                    items_data.append([
                        Paragraph(item.get('description', 'N/A'), normal_style),
                        Paragraph(str(item.get('quantity', 1)), normal_style),
                        Paragraph(f"£{item.get('price', 0):.2f}", normal_style),
                        Paragraph(f"£{(item.get('quantity', 1) * item.get('price', 0)):.2f}", normal_style)
                    ])
            else:
                items_data.append([
                    Paragraph(f"{project.title} - {invoice.invoice_type.title()} Invoice", normal_style),
                    Paragraph("1", normal_style),
                    Paragraph(f"£{invoice.amount:.2f}", normal_style),
                    Paragraph(f"£{invoice.amount:.2f}", normal_style)
                ])
            
            items_table = Table(items_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch], hAlign='LEFT')
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), title_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
            ]))
            story.append(items_table)
            story.append(Spacer(1, 0.3*inch))
            
            # Calculate actual total cost from items
            actual_total_cost = 0.0
            if invoice.items:
                for item in invoice.items:
                    actual_total_cost += item.get('quantity', 1) * item.get('price', 0)
            else:
                actual_total_cost = invoice.amount
            
            total_data = [
                ['', '', Paragraph("<b>Total Cost:</b>", bold_style), Paragraph(f"£{actual_total_cost:.2f}", normal_style)],
                ['', '', Paragraph("<b>Total Due:</b>", bold_style), Paragraph(f"<b>£{invoice.amount:.2f}</b>", bold_style)],
            ]
            
            total_table = Table(total_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch], hAlign='RIGHT')
            total_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('FONTNAME', (1, 1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (1, 1), (-1, -1), 14),
            ]))
            story.append(total_table)
            story.append(Spacer(1, 0.3*inch))
            
            if invoice.payment_terms:
                story.append(Paragraph("PAYMENT TERMS", header_style))
                story.append(Paragraph(invoice.payment_terms, normal_style))
                story.append(Spacer(1, 0.2*inch))
            
            if invoice.notes:
                story.append(Paragraph("NOTES", header_style))
                story.append(Paragraph(invoice.notes, normal_style))
                story.append(Spacer(1, 0.2*inch))
            
            story.append(Spacer(1, 0.5*inch))
            story.append(Paragraph("Thank you for your business!", ParagraphStyle('Footer', parent=styles['Normal'], fontSize=10, textColor=colors.gray, alignment=1)))
            
            doc.build(story)
            buffer.seek(0)
            
            pdf_data = buffer.getvalue()
            
            with open(cache_path, 'wb') as f:
                f.write(pdf_data)
            
            logger.info(f"Generated and cached PDF for invoice {invoice_id}")
            
            buffer.seek(0)
            return send_file(
                buffer,
                as_attachment=True,
                download_name=f"Invoice_{invoice.invoice_number}.pdf",
                mimetype='application/pdf'
            )
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            return jsonify({"error": "Failed to generate PDF"}), 500

    def api_generate_invoice(self):
        try:
            data = request.json or {}
            project_id = data.get('project_id')
            invoice_type = data.get('invoice_type', 'milestone')
            custom_amount = data.get('custom_amount')
            due_days = data.get('due_days', 30)
            payment_terms = data.get('payment_terms', f"Payment due within {due_days} days")
            payment_methods = data.get('payment_methods', 'PayPal, Bank Transfer')
            late_fee = data.get('late_fee', '5% per month on overdue amount')
            early_discount = data.get('early_discount', '2% discount if paid within 10 days')
            notes = data.get('notes', 'Thank you for your business!')
            
            if not project_id:
                return jsonify({"error": "Project ID is required"}), 400
            
            project = db.session.get(Project, project_id)
            if not project:
                return jsonify({"error": "Project not found"}), 404
            
            existing = Invoice.query.filter_by(
                project_id=project_id,
                invoice_type=invoice_type,
                status='pending'
            ).first()
            
            if existing:
                return jsonify({
                    "error": "A pending invoice of this type already exists",
                    "existing_invoice": existing.id
                }), 400
            
            if custom_amount and custom_amount > 0:
                amount = custom_amount
            else:
                if invoice_type == 'completion':
                    amount = project.price - project.amount_paid
                else:
                    amount = project.price * 0.5
            
            if amount <= 0:
                return jsonify({"error": "Invalid invoice amount"}), 400
            
            due_date = date.today() + timedelta(days=int(due_days))
            items = [{
                'description': f"{project.title} - {invoice_type.title()} Invoice",
                'quantity': 1,
                'price': amount
            }]
            
            invoice = Invoice(
                project_id=project_id,
                client_id=project.client_user_id,
                invoice_number=self.finance.generate_invoice_number(),
                invoice_type=invoice_type,
                amount=amount,
                due_date=due_date,
                status='pending',
                items=items,
                payment_terms=payment_terms,
                notes=notes
            )
            
            db.session.add(invoice)
            db.session.commit()
            
            self.comms.send_notification(
                user_id=project.client_user_id,
                notification_type="payment",
                title="New Invoice Generated",
                message=f"Invoice {invoice.invoice_number} has been generated. Amount: £{amount:.2f}",
                data={"invoice_id": invoice.id, "invoice_number": invoice.invoice_number, "amount": amount}
            )
            
            self.comms.send_invoice_email(
                invoice,
                payment_methods=payment_methods,
                late_fee=late_fee,
                early_discount=early_discount
            )
            
            return jsonify({
                "status": "success",
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "amount": amount
            })
        except Exception as e:
            logger.error(f"Error generating invoice: {str(e)}")
            db.session.rollback()
            return jsonify({"error": "Failed to generate invoice"}), 500

    def api_resend_invoice_email(self, invoice_id):
        try:
            invoice = db.session.get(Invoice, invoice_id)
            if not invoice:
                return jsonify({"error": "Invoice not found"}), 404
            
            payment_methods = os.environ.get('PAYMENT_METHODS', 'PayPal, Bank Transfer')
            late_fee = os.environ.get('LATE_FEE', '5% per month on overdue amount')
            early_discount = os.environ.get('EARLY_DISCOUNT', '2% discount if paid within 10 days')
            
            self.comms.send_invoice_email(
                invoice,
                payment_methods=payment_methods,
                late_fee=late_fee,
                early_discount=early_discount
            )
            
            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Error resending invoice email: {str(e)}")
            return jsonify({"error": "Failed to resend invoice email"}), 500

    def api_mark_invoice_paid(self, invoice_id):
        try:
            invoice = db.session.get(Invoice, invoice_id)
            if not invoice:
                return jsonify({"error": "Invoice not found"}), 404
            
            if invoice.status == 'paid':
                return jsonify({"error": "Invoice is already paid"}), 400
            
            invoice.status = 'paid'
            invoice.paid_at = datetime.now(timezone.utc)
            
            if invoice.project:
                invoice.project.amount_paid = float(invoice.project.amount_paid or 0) + invoice.amount
            
            self.finance.invalidate_pdf_cache(invoice_id)
            
            db.session.commit()
            
            self.comms.send_notification(
                user_id=invoice.client_id,
                notification_type="payment",
                title="Payment Received",
                message=f"Invoice {invoice.invoice_number} has been marked as paid.",
                data={"invoice_id": invoice.id, "amount": invoice.amount}
            )
            
            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Error marking invoice as paid: {str(e)}")
            db.session.rollback()
            return jsonify({"error": "Failed to mark invoice as paid"}), 500

    def get_notifications(self):
        try:
            uid = session.get('user_id')
            if not uid:
                return jsonify({"error": "Unauthorized"}), 401
            
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            notification_type = request.args.get('type', 'all')
            status_filter = request.args.get('status', 'all')
            
            query = Notification.query.filter_by(user_id=uid)
            
            if notification_type != 'all':
                query = query.filter_by(type=notification_type)
            
            if status_filter == 'unread':
                query = query.filter_by(read=False)
            elif status_filter == 'read':
                query = query.filter_by(read=True)
            
            notifications = query.order_by(Notification.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
            
            notification_list = [{
                'id': n.id,
                'type': n.type,
                'title': n.title,
                'message': n.message,
                'data': n.data,
                'read': n.read,
                'created_at': n.created_at.isoformat()
            } for n in notifications.items]
            
            return jsonify({
                "notifications": notification_list,
                "total": notifications.total,
                "pages": notifications.pages,
                "current_page": notifications.page
            })
        except Exception as e:
            logger.error(f"Error getting notifications: {str(e)}")
            return jsonify({"error": "Failed to fetch notifications"}), 500
    
    def get_notification_stats(self):
        try:
            uid = session.get('user_id')
            if not uid:
                return jsonify({"error": "Unauthorized"}), 401
            
            total = Notification.query.filter_by(user_id=uid).count()
            unread = Notification.query.filter_by(user_id=uid, read=False).count()
            read = Notification.query.filter_by(user_id=uid, read=True).count()
            
            return jsonify({"total": total, "unread": unread, "read": read})
        except Exception as e:
            logger.error(f"Error getting notification stats: {str(e)}")
            return jsonify({"error": "Failed to fetch stats"}), 500
    
    def mark_notification_read(self, notification_id):
        try:
            uid = session.get('user_id')
            if not uid:
                return jsonify({"error": "Unauthorized"}), 401
            
            notification = db.session.get(Notification, notification_id)
            if not notification or notification.user_id != uid:
                return jsonify({"error": "Notification not found"}), 404
            
            notification.read = True
            db.session.commit()
            
            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")
            return jsonify({"error": "Failed to mark as read"}), 500
    
    def mark_all_notifications_read(self):
        try:
            uid = session.get('user_id')
            if not uid:
                return jsonify({"error": "Unauthorized"}), 401
            
            Notification.query.filter_by(user_id=uid, read=False).update({'read': True})
            db.session.commit()
            
            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {str(e)}")
            return jsonify({"error": "Failed to mark all as read"}), 500
    
    def delete_notification(self, notification_id):
        try:
            uid = session.get('user_id')
            if not uid:
                return jsonify({"error": "Unauthorized"}), 401
            
            notification = db.session.get(Notification, notification_id)
            if not notification or notification.user_id != uid:
                return jsonify({"error": "Notification not found"}), 404
            
            db.session.delete(notification)
            db.session.commit()
            
            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Error deleting notification: {str(e)}")
            return jsonify({"error": "Failed to delete notification"}), 500
    
    def delete_read_notifications(self):
        try:
            uid = session.get('user_id')
            if not uid:
                return jsonify({"error": "Unauthorized"}), 401
            
            Notification.query.filter_by(user_id=uid, read=True).delete()
            db.session.commit()
            
            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Error deleting read notifications: {str(e)}")
            return jsonify({"error": "Failed to delete read notifications"}), 500
    
    def get_admin_notifications(self):
        """Get notifications for admin users with filtering and pagination"""
        try:
            uid = session.get('user_id')
            role = session.get('role', '').lower()
            if not uid or role != 'admin':
                return jsonify({"error": "Unauthorized"}), 401

            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            notification_type = request.args.get('type', 'all')
            status_filter = request.args.get('status', 'all')

            # Admin users see all notifications in the system, not just their own
            query = Notification.query

            if notification_type != 'all':
                query = query.filter_by(type=notification_type)

            if status_filter == 'unread':
                query = query.filter_by(read=False)
            elif status_filter == 'read':
                query = query.filter_by(read=True)

            notifications = query.order_by(Notification.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

            notification_list = [{
                'id': n.id,
                'type': n.type,
                'title': n.title,
                'message': n.message,
                'data': n.data,
                'read': n.read,
                'created_at': n.created_at.isoformat(),
                'user_id': n.user_id,
                'target_role': n.target_role
            } for n in notifications.items]

            return jsonify({
                "notifications": notification_list,
                "total": notifications.total,
                "pages": notifications.pages,
                "current_page": notifications.page
            })
        except Exception as e:
            logger.error(f"Error getting admin notifications: {str(e)}")
            return jsonify({"error": "Failed to fetch notifications"}), 500

    def get_admin_notification_stats(self):
        """Get notification statistics for admin users"""
        try:
            uid = session.get('user_id')
            role = session.get('role', '').lower()
            if not uid or role != 'admin':
                return jsonify({"error": "Unauthorized"}), 401

            # Admin sees all system notifications
            total = Notification.query.count()
            unread = Notification.query.filter_by(read=False).count()
            read = Notification.query.filter_by(read=True).count()

            return jsonify({"total": total, "unread": unread, "read": read})
        except Exception as e:
            logger.error(f"Error getting admin notification stats: {str(e)}")
            return jsonify({"error": "Failed to fetch stats"}), 500

    def mark_admin_notification_read(self, notification_id):
        """Mark a specific admin notification as read"""
        try:
            uid = session.get('user_id')
            role = session.get('role', '').lower()
            if not uid or role != 'admin':
                return jsonify({"error": "Unauthorized"}), 401

            notification = db.session.get(Notification, notification_id)
            if not notification:
                return jsonify({"error": "Notification not found"}), 404

            notification.read = True
            db.session.commit()

            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Error marking admin notification as read: {str(e)}")
            return jsonify({"error": "Failed to mark as read"}), 500

    def mark_all_admin_notifications_read(self):
        """Mark all admin notifications as read"""
        try:
            uid = session.get('user_id')
            role = session.get('role', '').lower()
            if not uid or role != 'admin':
                return jsonify({"error": "Unauthorized"}), 401

            # Admin can mark all system notifications as read
            Notification.query.filter_by(read=False).update({'read': True})
            db.session.commit()

            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Error marking all admin notifications as read: {str(e)}")
            return jsonify({"error": "Failed to mark all as read"}), 500

    def delete_admin_notification(self, notification_id):
        """Delete a specific admin notification"""
        try:
            uid = session.get('user_id')
            role = session.get('role', '').lower()
            if not uid or role != 'admin':
                return jsonify({"error": "Unauthorized"}), 401

            notification = db.session.get(Notification, notification_id)
            if not notification:
                return jsonify({"error": "Notification not found"}), 404

            db.session.delete(notification)
            db.session.commit()

            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Error deleting admin notification: {str(e)}")
            return jsonify({"error": "Failed to delete notification"}), 500

    def delete_read_admin_notifications(self):
        """Delete all read admin notifications"""
        try:
            uid = session.get('user_id')
            role = session.get('role', '').lower()
            if not uid or role != 'admin':
                return jsonify({"error": "Unauthorized"}), 401

            # Admin can delete all read notifications from the system
            Notification.query.filter_by(read=True).delete()
            db.session.commit()
            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Error deleting read admin notifications: {str(e)}")
            return jsonify({"error": "Failed to delete read notifications"}), 500

    def get_client_notifications(self):
        try:
            uid = session.get('user_id')
            if not uid:
                return jsonify({"error": "Unauthorized"}), 401
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            notification_type = request.args.get('type', 'all')
            status_filter = request.args.get('status', 'all')
            
            query = Notification.query.filter_by(user_id=uid)
            if notification_type != 'all':
                query = query.filter_by(type=notification_type)
            
            if status_filter == 'unread':
                query = query.filter_by(read=False)
            elif status_filter == 'read':
                query = query.filter_by(read=True)
            
            notifications = query.order_by(Notification.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
            notification_list = [{
                'id': n.id,
                'type': n.type,
                'title': n.title,
                'message': n.message,
                'data': n.data,
                'read': n.read,
                'created_at': n.created_at.isoformat()
            } for n in notifications.items]
            return jsonify({
                "notifications": notification_list,
                "total": notifications.total,
                "pages": notifications.pages,
                "current_page": notifications.page
            })
        except Exception as e:
            logger.error(f"Error getting client notifications: {str(e)}")
            return jsonify({"error": "Failed to fetch notifications"}), 500
    
    def get_client_notification_stats(self):
        try:
            uid = session.get('user_id')
            if not uid:
                return jsonify({"error": "Unauthorized"}), 401
            
            total = Notification.query.filter_by(user_id=uid).count()
            unread = Notification.query.filter_by(user_id=uid, read=False).count()
            read = Notification.query.filter_by(user_id=uid, read=True).count()
            return jsonify({"total": total, "unread": unread, "read": read})
        except Exception as e:
            logger.error(f"Error getting client notification stats: {str(e)}")
            return jsonify({"error": "Failed to fetch stats"}), 500
    
    def mark_client_notification_read(self, notification_id):
        try:
            uid = session.get('user_id')
            if not uid:
                return jsonify({"error": "Unauthorized"}), 401
            notification = db.session.get(Notification, notification_id)
            if not notification or notification.user_id != uid:
                return jsonify({"error": "Notification not found"}), 404
            
            notification.read = True
            db.session.commit()
            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Error marking client notification as read: {str(e)}")
            return jsonify({"error": "Failed to mark as read"}), 500
    
    def mark_all_client_notifications_read(self):
        try:
            uid = session.get('user_id')
            if not uid:
                return jsonify({"error": "Unauthorized"}), 401
            
            Notification.query.filter_by(user_id=uid, read=False).update({'read': True})
            db.session.commit()
            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Error marking all client notifications as read: {str(e)}")
            return jsonify({"error": "Failed to mark all as read"}), 500
    
    def delete_client_notification(self, notification_id):
        try:
            uid = session.get('user_id')
            if not uid:
                return jsonify({"error": "Unauthorized"}), 401
            notification = db.session.get(Notification, notification_id)
            if not notification or notification.user_id != uid:
                return jsonify({"error": "Notification not found"}), 404
            
            db.session.delete(notification)
            db.session.commit()
            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Error deleting client notification: {str(e)}")
            return jsonify({"error": "Failed to delete notification"}), 500
    
    def delete_read_client_notifications(self):
        try:
            uid = session.get('user_id')
            if not uid:
                return jsonify({"error": "Unauthorized"}), 401
            Notification.query.filter_by(user_id=uid, read=True).delete()
            db.session.commit()
            
            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Error deleting read client notifications: {str(e)}")
            return jsonify({"error": "Failed to delete read notifications"}), 500

    # Socket handlers
    def handle_connect(self):
        uid = session.get('user_id')
        if uid:
            join_room(f'user_{uid}')
            emit('unread_count', {'count': Notification.query.filter_by(user_id=uid, read=False).count()})
    
    def handle_disconnect(self):
        if session.get('user_id'): leave_room(f'user_{session.get("user_id")}')
    
    def handle_mark_read(self, data):
        try:
            notification_id = data.get('notification_id')
            uid = session.get('user_id')
            
            if not notification_id or not uid:
                return
            notification = db.session.get(Notification, notification_id)
            if notification and notification.user_id == uid:
                notification.read = True
                db.session.commit()
                emit('unread_count', {'count': Notification.query.filter_by(user_id=uid, read=False).count()}, room=f'user_{uid}')
        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")
    
    def handle_get_notifications(self, data):
        try:
            uid = session.get('user_id')
            if not uid:
                return
            page = data.get('page', 1)
            per_page = data.get('per_page', 20)
            notifications = Notification.query.filter_by(user_id=uid).order_by(Notification.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
            notification_list = [{
                'id': n.id,
                'type': n.type,
                'title': n.title,
                'message': n.message,
                'data': n.data,
                'read': n.read,
                'created_at': n.created_at.isoformat()
            } for n in notifications.items]
            emit('notifications', {
                'notifications': notification_list,
                'total': notifications.total,
                'pages': notifications.pages,
                'current_page': notifications.page
            }, room=f'user_{uid}')
        except Exception as e:
            logger.error(f"Error getting notifications: {str(e)}")

    def run(self, host="0.0.0.0", port=5000, debug=False, use_reloader=False):
        self.logger.info(f"Starting Emma's server on port {port} (debug={debug}, auto_reload={use_reloader})")
        self.socketio.run(self.app, host=host, port=port, debug=debug, use_reloader=use_reloader)

# --- SERVER BOOTSTRAP ---
if __name__ == "__main__":
    server = EmmaServer()
    DatabaseManager.initialize_database(server.app, db)
    
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    auto_reload = os.environ.get("FLASK_AUTO_RELOAD", "True").lower() == "true"
    use_reloader = auto_reload and not server.config.is_production_env
    
    server.run(host="0.0.0.0", port=port, debug=debug_mode, use_reloader=use_reloader)