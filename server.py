import os
import re
import secrets
import bcrypt
import logging
from datetime import datetime, date, timedelta, timezone
import requests
import json
import base64
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import (
    Flask, jsonify, request, render_template,
    redirect, session, url_for, send_file, abort
)
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- SECURE SECRET KEY HANDLING ---
# In multi-worker environments (e.g. Gunicorn), generating a secret key dynamically 
# on every startup will cause workers to have different keys, instantly invalidating sessions.
# We read from environment variables first. As a fallback, we store a persistent key locally.
SECRET_KEY_FILE = Path(".flask_secret_key")
env_secret = os.environ.get("FLASK_SECRET_KEY")

if env_secret:
    app.secret_key = env_secret
else:
    if SECRET_KEY_FILE.exists():
        app.secret_key = SECRET_KEY_FILE.read_text().strip()
    else:
        generated_key = secrets.token_hex(32)
        try:
            SECRET_KEY_FILE.write_text(generated_key)
            app.secret_key = generated_key
        except Exception as e:
            logger.warning(f"Could not save persistent secret key to disk: {e}. Falling back to single-session ephemeral key.")
            app.secret_key = generated_key

# Determine if running in production
_is_production_env = (
    os.environ.get("FLASK_ENV", "").lower() == "production" or
    os.environ.get("ENV", "").lower() == "production" or
    os.environ.get("PRODUCTION", "").lower() in ("1", "true", "yes")
)
_secure_session_cookie = _is_production_env or os.environ.get("HTTPS_ONLY", "").lower() in ("1", "true", "yes")

# Session security settings - production-hardened, local-development friendly
app.config.update(
    SESSION_COOKIE_SECURE=_secure_session_cookie,  # Enforce HTTPS only in production/HTTPS mode
    SESSION_COOKIE_HTTPONLY=True,        # Prevent cross-site scripting (XSS) cookie extraction
    SESSION_COOKIE_SAMESITE='Lax',       # Mitigate Cross-Site Request Forgery (CSRF)
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),  # Auto session timeout
    SESSION_COOKIE_NAME='__Secure-personal_app_session' if _secure_session_cookie else 'personal_app_session'
)

# CSRF Configuration (To be fully integrated with frontend template forms using {% csrf_token %} or headers)
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # Cache static assets for 1 year

# Rate limiting using client IP address
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100000 per hour"],
    storage_uri="memory://"  # Safe, low-overhead default in-memory backend
)

# Granular, strict limiters for secure endpoints
login_limiter = limiter.limit("5000 per minute")
register_limiter = limiter.limit("5000 per minute")
api_limiter = limiter.limit("1000000 per hour")
admin_limiter = limiter.limit("200000 per hour")

# --- FILE UPLOAD CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / 'uploads'
ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'mkv', 'md',
    'doc', 'docx', 'xls', 'xlsx', 'zip', 'ppt', 'pptx', 'webm', 'mp3', 'wav'
}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB maximum file limit
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE  # Hard limit enforced by Flask on incoming payloads

# Ensure the upload directory exists securely
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- PAYPAL CONFIGURATION ---
PAYPAL_MODE = os.environ.get("PAYPAL_MODE", "sandbox")
PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
PAYPAL_API_BASE = "https://api.sandbox.paypal.com" if PAYPAL_MODE == "sandbox" else "https://api.paypal.com"

def get_paypal_access_token():
    """Get PayPal OAuth access token securely"""
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        logger.error("PayPal credentials not configured")
        return None
    try:
        auth = base64.b64encode(f"{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        response = requests.post(
            f"{PAYPAL_API_BASE}/v1/oauth2/token",
            headers=headers,
            data={"grant_type": "client_credentials"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        
        logger.error(f"PayPal token error: {response.status_code}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"PayPal API request failed: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error getting PayPal token: {str(e)}")
        return None

# --- DATABASE CONFIGURATION ---
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    if DATABASE_URL.startswith("postgresql://") and "sslmode=" not in DATABASE_URL:
        if any(host in DATABASE_URL for host in ("render.com", "heroku", "aws")):
            sep = "&" if "?" in DATABASE_URL else "?"
            DATABASE_URL = f"{DATABASE_URL}{sep}sslmode=require"

    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    logger.info("Using DATABASE_URL for SQLALCHEMY_DATABASE_URI")
else:
    if _is_production_env:
        logger.error("DATABASE_URL is not set in production environment. Aborting startup.")
        raise RuntimeError("DATABASE_URL must be set in production environment")

    logger.warning("DATABASE_URL not set. Falling back to SQLite for development.")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///personalapp.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# --- MODELS ---

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=True)  # nullable for record-only placeholders
    role = db.Column(db.String(50), default="client")
    email = db.Column(db.String(255))
    company = db.Column(db.String(255))
    type = db.Column(db.String(50))  # e.g. "record_only"
    date_added = db.Column(db.Date)

    projects = db.relationship("Project", backref="client", lazy=True, cascade="all, delete-orphan")
    messages = db.relationship("Message", backref="client_user", lazy=True, cascade="all, delete-orphan")

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

class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    from_role = db.Column("sender_role", db.String(50))  # "admin" or "client"
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    type = db.Column(db.String(50))
    payment_data = db.Column(db.JSON)

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
    file_size = db.Column(db.Integer)  # in bytes
    mime_type = db.Column(db.String(100))
    uploaded_by_role = db.Column(db.String(50))  # "admin" or "client"
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    message = db.relationship("Message", backref="attachments")
    uploader = db.relationship("User", backref="uploaded_files")

def initialize_database():
    """Create database tables safely if they do not exist"""
    try:
        logger.info("Initializing database...")
        with app.app_context():
            db.create_all()
            logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise

# --- SECURITY UTILITIES & CHECKS ---

def hash_password(password: str) -> str:
    """Hash password using bcrypt for secure storage"""
    salt = bcrypt.gensalt(rounds=12) # Secure work factor
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def validate_username(username: str) -> bool:
    """Validate username format and length (alphanumeric, dashes, underscores, 3-50 chars)"""
    if not username or len(username) < 3 or len(username) > 50:
        return False
    return bool(re.match(r'^[a-zA-Z0-9\-_]+$', username))

def validate_password(password: str):
    """Validate password strength. Returns (valid, message)"""
    if not password:
        return False, "Password is required"
    if len(password) < 5:  # Standard secure baseline length
        return False, "Password must be at least 5 characters"
    if len(password) > 128:
        return False, "Password must not exceed 128 characters"
    
    # Check for complexity
    has_digit = any(c.isdigit() for c in password)    
    if not (has_digit):
        return False, "Password must contain numbers"
    return True, ""

def validate_email(email: str) -> bool:
    """Validate email format securely"""
    if not email:
        return True  # Email is optional
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return len(email) <= 255 and bool(re.match(pattern, email))

def validate_project_title(title: str) -> bool:
    """Validate project title (3-255 chars)"""
    return bool(title) and 3 <= len(title) <= 255

def validate_amount(amount: float) -> bool:
    """Validate payment amount (0.01 to 999,999.99)"""
    try:
        return 0.01 <= float(amount) <= 999999.99
    except (ValueError, TypeError):
        return False

def validate_rating(rating: int) -> bool:
    """Validate rating is between 1 and 5"""
    try:
        return 1 <= int(rating) <= 5
    except (ValueError, TypeError):
        return False

def sanitize_input(input_string: str) -> str:
    """Sanitize user input to prevent basic HTML/XSS injection"""
    if not input_string:
        return ""
    # Strip basic HTML tags
    clean = re.sub(r'<[^>]*>', '', input_string)
    return clean.strip()

# --- DECORATORS FOR ACCESS CONTROL (ROLE-BASED AUTHORIZATION) ---

def login_required(f):
    """Decorator to enforce active session login validation"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            logger.warning(f"Unauthorized access attempt blocked from IP {get_remote_address()} on route {request.path}")
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for("login"))
        
        # Verify user still exists in the DB
        user = User.query.get(user_id)
        if not user:
            session.clear()
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({"error": "User account no longer exists"}), 401
            return redirect(url_for("login"))
            
        # Update session timeout activity
        session["last_activity"] = datetime.now(timezone.utc).isoformat()
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to enforce admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First verify login status
        user_id = session.get("user_id")
        role = session.get("role")
        
        if not user_id or not role or role.lower() != "admin":
            logger.warning(f"Access Denied: Non-admin {user_id} attempted access to administrative route {request.path}")
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({"error": "Forbidden"}), 403
            return redirect(url_for("dashboard"))
            
        return f(*args, **kwargs)
    return decorated_function

# --- SECURE FILE PATH SANITIZATION ---

def get_safe_file_path(filename: str) -> Path:
    """
    Ensure the path constructed does not escape the defined uploads directory via path traversal tricks.
    Returns safe Path object or aborts request with a 400 Bad Request error.
    """
    # Restrict to clean secure filename
    clean_filename = secure_filename(filename)
    if not clean_filename:
        abort(400, "Invalid file name")
        
    resolved_path = (UPLOADS_DIR / clean_filename).resolve()
    
    # Check if directory boundaries are strictly respected
    if not resolved_path.is_relative_to(UPLOADS_DIR.resolve()):
        logger.error(f"Directory traversal attempt detected! Path: {resolved_path}")
        abort(400, "Directory traversal path attempt detected!")
        
    return resolved_path

# --- ROUTES ---

@app.route("/")
@login_required
def dashboard():
    role = session.get("role", "client")
    if role.lower() == "admin":
        users = User.query.all()
        clients = [u for u in users if (u.role or "").lower() == "client"]
        projects = Project.query.all()
        return render_template("index.html", clients=len(clients), projects=len(projects))
    else:
        return redirect(url_for("client_portal"))

@app.route("/login", methods=["GET", "POST"])
@login_limiter
def login():
    try:
        if request.method == "GET":
            return render_template("login.html")

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            return render_template("login.html", error="Username and password are required")
        
        if not validate_username(username):
            return render_template("login.html", error="Invalid username format")

        user = User.query.filter_by(username=username).first()
        
        # Guard against timing attacks by performing a dummy hash comparison if user doesn't exist
        dummy_hash = "$2b$12$Z0bT5.YfD98O47M6jIqR9unbKkX3iB/Yt/Yh35Xq.RzR9M/Yt/Yh3"
        if not user or not user.password:
            bcrypt.checkpw(password.encode('utf-8'), dummy_hash.encode('utf-8'))
            return render_template("login.html", error="Invalid credentials")
        
        if not verify_password(password, user.password):
            logger.warning(f"Failed login attempt for user: {username} from IP {get_remote_address()}")
            return render_template("login.html", error="Invalid credentials")
        
        # Establish dynamic session state safely
        session.clear()
        session["user"] = user.username
        session["user_id"] = user.id
        session["role"] = user.role or "client"
        session.permanent = True  # Enforce lifetime set in cookie configuration
        
        logger.info(f"User {username} (ID: {user.id}) logged in successfully.")
        return redirect(url_for("dashboard"))
        
    except Exception as e:
        logger.error(f"Login processing error: {str(e)}")
        return render_template("login.html", error="An error occurred during login")

@app.route("/register", methods=["GET", "POST"])
@register_limiter
def register():
    try:
        if request.method == "GET":
            return render_template("login.html", register=True)

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            return render_template("login.html", register=True, error="Username and password are required")
        
        if not validate_username(username):
            return render_template("login.html", register=True, error="Invalid username format")
        
        # Enforce password strength validation
        valid, msg = validate_password(password)
        if not valid:
            return render_template("login.html", register=True, error=msg)

        # Secure check for pre-existing user records
        existing = User.query.filter(
            db.func.lower(User.username) == username.lower()
        ).first()
        if existing:
            return render_template("login.html", register=True, error="User already exists")

        total_users = User.query.count()
        role = "admin" if total_users == 0 else "client"

        new_user = User(
            username=username,
            password=hash_password(password),
            role=role,
            date_added=date.today()
        )
        
        db.session.add(new_user)
        db.session.commit()
     
        session.clear()
        session["user"] = new_user.username
        session["user_id"] = new_user.id
        session["role"] = new_user.role
        session.permanent = True
        
        logger.info(f"New user registered: {username} (role: {role})")
        return redirect(url_for("client_register"))
        
    except Exception as e:
        logger.error(f"Register error: {str(e)}")
        db.session.rollback()
        return render_template("login.html", register=True, error="An error occurred during registration")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# --- CLIENT PORTAL ---

@app.route("/client/dashboard")
@login_required
def client_portal():
    return render_template("client_portal.html")
    
@app.route("/client/register")
@login_required
def client_register():
    return render_template("client_register.html")

@app.route("/api/services")
@api_limiter
def services_api():
    services = Service.query.all()
    return jsonify([
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "price": s.price,
            "icon": s.icon
        } for s in services
    ])

@app.route("/services")
@login_required
def services_page():
    services = Service.query.all()
    return render_template("services.html", services=services)

@app.route("/client_billing")
@login_required
def client_billing():
    return render_template("client_billing.html")

@app.route("/client/order")
@login_required
def order_page():
    return render_template("client_order.html")

@app.route("/client_feedback")
@login_required
def client_feedback():
    return render_template("client_feedback.html")

@app.route("/api/orders", methods=["POST"])
@login_required
def place_order():
    # Handle both JSON and multipart/form-data
    if request.content_type and 'multipart/form-data' in request.content_type:
        service_name = sanitize_input(request.form.get("service_name", ""))
        description = sanitize_input(request.form.get("description", ""))
        budget = sanitize_input(request.form.get("budget", ""))
        price_str = request.form.get("price", "0")
        uploaded_files = request.files.getlist('files')
    else:
        data = request.json or {}
        service_name = sanitize_input(data.get("service_name", ""))
        description = sanitize_input(data.get("description", ""))
        budget = sanitize_input(data.get("budget", ""))
        price_str = data.get("price", "0")
        uploaded_files = []
    
    try:
        price = float(price_str)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid price format"}), 400

    if not service_name or len(service_name) > 255:
        return jsonify({"error": "Service name is required and must be under 255 chars"}), 400

    current_user_id = session.get("user_id")
    current_username = session.get("user", "Guest")

    new_project = Project(
        client_user_id=current_user_id,
        client_name=current_username,
        title=service_name,
        desc=description,
        budget_estimate=budget,
        status="Pending Approval",
        date_created=date.today(),
        amount_paid=0.0,
        price=price
    )
    db.session.add(new_project)
    db.session.flush()

    content = (
        f"💼 NEW ORDER: Client '{current_username}' placed order for "
        f"'{service_name}' | Est. Price: £{price:.2f} | Status: Awaiting Review"
    )
    msg = Message(
        client_id=current_user_id,
        from_role="client",
        content=content,
        timestamp=datetime.now(timezone.utc)
    )
    db.session.add(msg)
    db.session.flush()

    # Handle file attachments
    if uploaded_files:
        for file in uploaded_files:
            if file and file.filename and allowed_file(file.filename):
                # Generate secure filename
                original_filename = secure_filename(file.filename)
                # Add timestamp to prevent collisions
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                random_suffix = secrets.token_hex(4)
                stored_filename = f"{timestamp}_{random_suffix}_{original_filename}"
                
                # Save file to uploads directory
                file_path = UPLOADS_DIR / stored_filename
                try:
                    file.save(str(file_path))
                    
                    # Create file attachment record
                    attachment = FileAttachment(
                        message_id=msg.id,
                        client_id=current_user_id,
                        original_filename=original_filename,
                        stored_filename=stored_filename,
                        file_size=file.content_length,
                        mime_type=file.content_type,
                        uploaded_by_role="client"
                    )
                    db.session.add(attachment)
                except Exception as e:
                    logger.error(f"Failed to save file {original_filename}: {str(e)}")
                    continue

    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Order transmitted successfully. Emmanuel will review and get back to you shortly."
    })

@app.route("/api/profile")
def get_profile():
    # Public route containing read-only profiles
    profile_data = {
        "name": "Emmanuel Ugwu",
        "headline": "Expert Freelance Software Developer",
        "location": "Dudley, England, United Kingdom",
        "about": "Currently working as a Freelance Software Developer...",
        "services": [
            {"name": "Application Development", "icon": "fa-mobile-screen"},
            {"name": "Database Development", "icon": "fa-database"}
        ]
    }
    return jsonify(profile_data)

@app.route("/clients")
@login_required
@admin_required
def clients_page():
    return render_template("clients.html")

@app.route("/projects")
@login_required
def projects_page():
    return render_template("projects.html")

# --- API: DASHBOARD DATA ---

@app.route("/api/dashboard")
@login_required
def dashboard_data():
    role = session.get("role", "client")
    if role.lower() == "admin":
        projects = Project.query.all()
    else:
        uid = session.get("user_id")
        projects = Project.query.filter_by(client_user_id=uid).all()

    status_counts = {}
    total_revenue = 0.0
    total_paid = 0.0

    for p in projects:
        st = p.status or "Pending"
        status_counts[st] = status_counts.get(st, 0) + 1
        total_revenue += float(p.price or 0)
        total_paid += float(p.amount_paid or 0)

    return jsonify({
        "status_counts": status_counts,
        "total_revenue": total_revenue,
        "total_paid": total_paid
    })

# --- API: CLIENTS ---

@app.route("/api/clients")
@login_required
@admin_required
def get_clients():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        
        if page < 1 or per_page < 1:
            return jsonify({"error": "Invalid pagination parameters"}), 400

        # Query and return only true clients
        users = User.query.filter_by(role="client").all()

        return jsonify([
            {
                "id": c.id,
                "username": c.username,
                "email": c.email,
                "company": c.company,
                "role": c.role,
                "type": c.type,
                "date_added": c.date_added.isoformat() if c.date_added else None
            } for c in users
        ])
    except Exception as e:
        logger.error(f"Error fetching clients: {str(e)}")
        return jsonify({"error": "Failed to fetch clients"}), 500

# --- API: PROJECTS ---

@app.route("/api/test")
def test_connection():
    """System health verification check"""
    try:
        project_count = Project.query.count()
        user_count = User.query.count()
        logged_in = session.get("user_id") is not None
        
        return jsonify({
            "status": "success",
            "database_connected": True,
            "projects_count": project_count,
            "users_count": user_count,
            "session": {
                "user": session.get("user"),
                "user_id": session.get("user_id"),
                "role": session.get("role"),
                "logged_in": logged_in
            }
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "error",
            "database_connected": False,
            "error": "Database connection failed"
        }), 500

@app.route("/api/projects")
@login_required
def get_projects():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        
        if page < 1 or per_page < 1:
            return jsonify({"error": "Invalid pagination parameters"}), 400
        
        role = session.get("role", "client")
        if role.lower() == "admin":
            query = Project.query.order_by(Project.date_created.desc())
        else:
            uid = session.get("user_id")
            query = Project.query.filter_by(client_user_id=uid).order_by(Project.date_created.desc())
        
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        projects_data = []
        for p in paginated.items:
            client_details = None
            try:
                if p.client_user_id and role.lower() == "admin":
                    client = User.query.get(p.client_user_id)
                    if client:
                        client_details = {
                            "email": client.email,
                            "company": client.company,
                            "date_added": client.date_added.isoformat() if client.date_added else None
                        }
            except Exception as client_error:
                logger.error(f"Error fetching client details for project {p.id}: {str(client_error)}")
            
            # Get attached files for this project's client (all files associated with this client)
            attached_files = []
            if p.client_user_id:
                try:
                    # Query all files where client_id matches the project's client_user_id
                    files = FileAttachment.query.filter_by(client_id=p.client_user_id).order_by(FileAttachment.uploaded_at.desc()).all()
                    logger.info(f"Found {len(files)} files for project {p.id} (client_id: {p.client_user_id})")
                    attached_files = [
                        {
                            "id": f.id,
                            "original_filename": f.original_filename,
                            "file_size": f.file_size,
                            "mime_type": f.mime_type,
                            "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else None,
                            "uploaded_by_role": f.uploaded_by_role,
                            "message_id": f.message_id
                        }
                        for f in files
                    ]
                except Exception as file_error:
                    logger.error(f"Error fetching files for project {p.id}: {str(file_error)}")

            project_data = {
                "id": p.id,
                "client_user_id": p.client_user_id,
                "client_name": p.client_name,
                "client_details": client_details,
                "title": p.title,
                "desc": p.desc,
                "budget_estimate": p.budget_estimate,
                "status": p.status,
                "date_created": p.date_created.isoformat() if p.date_created else None,
                "deadline": p.deadline.isoformat() if p.deadline else None,
                "amount_paid": float(p.amount_paid or 0),
                "price": float(p.price or 0),
                "outstanding_balance": float(p.price or 0) - float(p.amount_paid or 0),
                "attached_files": attached_files,
            }
            
            if p.deadline:
                today = date.today()
                delta = p.deadline - today
                project_data["days_until_deadline"] = delta.days
                project_data["deadline_status"] = (
                    "overdue" if delta.days < 0 else
                    "urgent" if delta.days <= 3 else
                    "warning" if delta.days <= 7 else
                    "normal"
                )
            
            projects_data.append(project_data)

        return jsonify({
            "data": projects_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": paginated.total,
                "pages": paginated.pages,
                "has_next": paginated.has_next,
                "has_prev": paginated.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Error in /api/projects: {str(e)}")
        return jsonify({"error": "Failed to load projects"}), 500

@app.route("/api/projects", methods=["POST"])
@login_required
def create_project():
    try:
        data = request.json or {}
        title = sanitize_input(data.get("title", ""))
        desc = sanitize_input(data.get("desc", ""))
        budget_estimate = sanitize_input(data.get("budget_estimate", ""))
        status = sanitize_input(data.get("status", "Pending Approval"))
        
        if not title or not validate_project_title(title):
            return jsonify({"error": "Project title must be 3-255 characters"}), 400
        
        role = session.get("role", "client")
        if role.lower() == "admin":
            client_id = data.get("client_user_id")
            if not client_id:
                return jsonify({"error": "client_user_id is required when creating as admin"}), 400
            client_user = User.query.get(client_id)
            if not client_user:
                return jsonify({"error": "Selected client does not exist"}), 404
            client_name = client_user.username
        else:
            client_id = session.get("user_id")
            client_name = session.get("user")
        
        deadline = None
        if data.get("deadline"):
            try:
                deadline = datetime.strptime(data.get("deadline"), "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"error": "Invalid deadline format. Use YYYY-MM-DD"}), 400
        
        try:
            price = float(data.get("price", 0.0))
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid price format"}), 400
        
        new_project = Project(
            client_user_id=client_id,
            client_name=client_name,
            title=title,
            desc=desc,
            budget_estimate=budget_estimate,
            status=status,
            deadline=deadline,
            price=price
        )
        
        db.session.add(new_project)
        db.session.commit()
        
        logger.info(f"Project created: {new_project.title} for {client_name}")
        
        return jsonify({
            "status": "success",
            "message": "Project created successfully",
            "project": {
                "id": new_project.id,
                "title": new_project.title,
                "status": new_project.status,
                "date_created": new_project.date_created.isoformat() if new_project.date_created else None,
                "deadline": new_project.deadline.isoformat() if new_project.deadline else None
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating project: {str(e)}")
        return jsonify({"error": "Failed to create project"}), 500

@app.route("/api/projects/<int:project_id>", methods=["PATCH"])
@login_required
@admin_required
def update_project(project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        data = request.json or {}
        
        if "status" in data:
            project.status = sanitize_input(data["status"])
            logger.info(f"Project {project_id} status updated to: {project.status}")
        
        if "amount_paid" in data:
            try:
                project.amount_paid = float(data["amount_paid"])
                logger.info(f"Project {project_id} payment updated to: {project.amount_paid}")
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid payment amount"}), 400
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Project updated successfully",
            "project": {
                "id": project.id,
                "title": project.title,
                "status": project.status,
                "amount_paid": project.amount_paid,
                "date_created": project.date_created.isoformat() if project.date_created else None,
                "deadline": project.deadline.isoformat() if project.deadline else None
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating project {project_id}: {str(e)}")
        return jsonify({"error": "Failed to update project"}), 500

@app.route("/api/projects/<int:project_id>/payment", methods=["POST"])
@login_required
@admin_required
def update_payment(project_id):
    data = request.json or {}
    try:
        amount = float(data.get("amount", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount"}), 400

    project = Project.query.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    project.amount_paid = float(project.amount_paid or 0) + amount
    db.session.commit()

    return jsonify({"status": "success"})

@app.route("/api/projects/<int:project_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_project(project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        logger.info(f"Admin deleting project {project_id}: '{project.title}'")
        
        db.session.delete(project)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": f"Project '{project.title}' deleted successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting project {project_id}: {str(e)}")
        return jsonify({"error": "Failed to delete project"}), 500

# --- API: CLIENT PAYMENT SUBMISSION (SECURED AGAINST IDOR) ---

@app.route("/api/payment/submit", methods=["POST"])
@login_required
def submit_payment():
    data = request.json or {}
    project_id = data.get("project_id")
    amount = data.get("amount")
    payment_method = sanitize_input(data.get("payment_method", "Bank Transfer"))

    if not project_id or not amount:
        return jsonify({"error": "Missing project_id or amount"}), 400

    try:
        amount = float(amount)
        project_id = int(project_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount or project_id"}), 400

    if not validate_amount(amount):
        return jsonify({"error": "Amount must be between 0.01 and 999,999.99"}), 400

    project = Project.query.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    # SECURED AGAINST IDOR: Enforce client access permissions to their own projects
    role = session.get("role", "client")
    current_user_id = session.get("user_id")
    if role.lower() != "admin" and project.client_user_id != current_user_id:
        logger.warning(f"IDOR Alert: User {current_user_id} attempted unauthorized payment for project {project_id}")
        return jsonify({"error": "Access denied"}), 403

    old_paid = float(project.amount_paid or 0)
    project.amount_paid = old_paid + amount
    outstanding = max(float(project.price or 0) - project.amount_paid, 0)

    payment_message = Message(
        client_id=project.client_user_id,
        from_role="client",
        content=(
            f"💳 PAYMENT SENT: Client '{session.get('user')}' submitted payment of £{amount:.2f} "
            f"for project '{project.title}' (ID: {project_id}) via {payment_method}. "
            f"Amount paid updated from £{old_paid:.2f} to £{project.amount_paid:.2f}. "
            f"Outstanding balance: £{outstanding:.2f}."
        ),
        timestamp=datetime.now(timezone.utc),
        type="payment_submission",
        payment_data={
            "project_id": project_id,
            "project_title": project.title,
            "amount": amount,
            "payment_method": payment_method,
            "previous_paid": old_paid,
            "new_paid": project.amount_paid,
            "project_total": float(project.price or 0)
        }
    )

    db.session.add(payment_message)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": f"Payment of £{amount:.2f} received successfully.",
        "project": {
            "id": project_id,
            "title": project.title,
            "amount_paid": project.amount_paid,
            "price": float(project.price or 0),
            "outstanding": outstanding
        }
    })

# --- API: PAYPAL PAYMENTS (SECURED AGAINST IDOR) ---

@app.route("/api/paypal/create-payment", methods=["POST"])
@login_required
def paypal_create_payment():
    try:
        data = request.json or {}
        project_id = data.get("project_id")
        amount = data.get("amount")

        if not project_id or not amount:
            return jsonify({"error": "Missing project_id or amount"}), 400

        try:
            amount = float(amount)
            project_id = int(project_id)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid amount or project_id"}), 400

        if not validate_amount(amount):
            return jsonify({"error": "Amount must be between 0.01 and 1,000,000"}), 400

        project = Project.query.get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        # SECURED AGAINST IDOR: Enforce client access permissions to their own projects
        role = session.get("role", "client")
        current_user_id = session.get("user_id")
        if role.lower() != "admin" and project.client_user_id != current_user_id:
            logger.warning(f"IDOR Alert: User {current_user_id} attempted PayPal payment generation for project {project_id}")
            return jsonify({"error": "Access denied"}), 403

        access_token = get_paypal_access_token()
        if not access_token:
            return jsonify({"error": "Failed to authenticate with PayPal"}), 500

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        payment_payload = {
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": url_for("paypal_execute_payment", _external=True),
                "cancel_url": url_for("paypal_cancel_payment", _external=True)
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": project.title,
                        "sku": f"PROJECT_{project_id}",
                        "price": str(round(amount, 2)),
                        "currency": "GBP",
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": str(round(amount, 2)),
                    "currency": "GBP",
                    "details": {
                        "subtotal": str(round(amount, 2))
                    }
                },
                "description": f"Payment for project: {project.title}",
                "custom": str(project_id)
            }]
        }

        response = requests.post(
            f"{PAYPAL_API_BASE}/v1/payments/payment",
            headers=headers,
            json=payment_payload,
            timeout=10
        )

        if response.status_code == 201:
            payment_data = response.json()
            payment_id = payment_data.get("id")
            
            approval_url = None
            for link in payment_data.get("links", []):
                if link.get("rel") == "approval_url":
                    approval_url = link.get("href")
                    break

            if approval_url:
                logger.info(f"PayPal payment created successfully: {payment_id}")
                session[f"paypal_payment_{project_id}"] = payment_id
                
                return jsonify({
                    "status": "success",
                    "payment_id": payment_id,
                    "approval_url": approval_url,
                    "message": "Redirecting to PayPal..."
                })
            else:
                logger.error("No approval URL found in PayPal response")
                return jsonify({"error": "No approval URL found in PayPal response"}), 500
        else:
            logger.error(f"PayPal payment creation failed: {response.status_code}")
            return jsonify({"error": "Failed to create PayPal payment"}), 400

    except Exception as e:
        logger.error(f"Error creating PayPal payment: {str(e)}")
        return jsonify({"error": "Failed to create payment"}), 500

@app.route("/api/paypal/execute-payment", methods=["GET", "POST"])
@login_required
def paypal_execute_payment():
    try:
        payment_id = request.args.get("paymentId")
        payer_id = request.args.get("PayerID")

        if not payment_id or not payer_id:
            return jsonify({"error": "Missing payment or payer ID"}), 400

        access_token = get_paypal_access_token()
        if not access_token:
            return jsonify({"error": "Failed to authenticate with PayPal"}), 500

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        execute_payload = {
            "payer_id": payer_id
        }

        response = requests.post(
            f"{PAYPAL_API_BASE}/v1/payments/payment/{payment_id}/execute",
            headers=headers,
            json=execute_payload,
            timeout=10
        )

        if response.status_code == 200:
            payment_data = response.json()
            
            transactions = payment_data.get("transactions", [])
            if not transactions:
                return jsonify({"error": "No transactions found"}), 400

            custom_data = transactions[0].get("custom", "")
            amount_data = transactions[0].get("amount", {})
            amount = float(amount_data.get("total", 0))

            try:
                project_id = int(custom_data)
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid project ID in transaction"}), 400

            project = Project.query.get(project_id)
            if not project:
                return jsonify({"error": "Project not found"}), 404

            # Verify current user context matching payment project
            role = session.get("role", "client")
            current_user_id = session.get("user_id")
            if role.lower() != "admin" and project.client_user_id != current_user_id:
                logger.warning(f"IDOR Alert: Unauthorized user context attempt on payment execution.")
                return jsonify({"error": "Access denied"}), 403

            old_paid = float(project.amount_paid or 0)
            project.amount_paid = old_paid + amount
            outstanding = max(float(project.price or 0) - project.amount_paid, 0)

            payment_message = Message(
                client_id=project.client_user_id,
                from_role="client",
                content=(
                    f"💳 PAYMENT RECEIVED: Client '{session.get('user')}' successfully paid £{amount:.2f} "
                    f"for project '{project.title}' (ID: {project_id}) via PayPal. "
                    f"Amount paid updated from £{old_paid:.2f} to £{project.amount_paid:.2f}. "
                    f"Outstanding balance: £{outstanding:.2f}."
                ),
                timestamp=datetime.now(timezone.utc),
                type="payment_submission",
                payment_data={
                    "project_id": project_id,
                    "project_title": project.title,
                    "amount": amount,
                    "payment_method": "PayPal",
                    "paypal_payment_id": payment_id,
                    "payer_id": payer_id,
                    "previous_paid": old_paid,
                    "new_paid": project.amount_paid,
                    "project_total": float(project.price or 0),
                    "status": "completed"
                }
            )

            db.session.add(payment_message)
            db.session.commit()

            logger.info(f"PayPal payment executed successfully: {payment_id}")

            return jsonify({
                "status": "success",
                "message": f"Payment of £{amount:.2f} received successfully!",
                "payment_id": payment_id,
                "project": {
                    "id": project_id,
                    "title": project.title,
                    "amount_paid": project.amount_paid,
                    "price": float(project.price or 0),
                    "outstanding": outstanding
                }
            })
        else:
            logger.error(f"PayPal payment execution failed: {response.status_code}")
            return jsonify({"error": "Payment execution failed"}), 400

    except Exception as e:
        logger.error(f"Error executing PayPal payment: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Failed to execute payment"}), 500

@app.route("/api/paypal/cancel-payment", methods=["GET"])
def paypal_cancel_payment():
    return jsonify({
        "status": "cancelled",
        "message": "Payment was cancelled by user"
    })

# --- API: ADMIN ADD CLIENT RECORD ---

@app.route("/api/clients/add", methods=["POST"])
@login_required
@admin_required
def admin_add_client_record():
    data = request.json or {}
    username = sanitize_input(data.get("username", ""))
    email = sanitize_input(data.get("email", "N/A"))
    company = sanitize_input(data.get("company", "N/A"))
    role = sanitize_input(data.get("role", "Client"))

    if not username:
        return jsonify({"error": "Name/Username required"}), 400
    
    if not validate_username(username):
        return jsonify({"error": "Invalid username format"}), 400
    
    if email != "N/A" and not validate_email(email):
        return jsonify({"error": "Invalid email format"}), 400

    existing = User.query.filter(db.func.lower(User.username) == username.lower()).first()
    if existing:
        return jsonify({"error": "This record already exists"}), 400

    new_user = User(
        username=username,
        email=email,
        company=company,
        role=role.lower(),
        type="record_only",
        date_added=date.today()
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    logger.info(f"Client record created: {username} by admin (ID: {session.get('user_id')})")
    
    return jsonify({
        "status": "success",
        "message": f"Client record for {username} created.",
        "user": {"id": new_user.id, "name": username}
    })

# --- API: MESSAGES THREAD ---

@app.route("/api/messages/<int:target_id>", methods=["GET", "POST"])
@login_required
def api_messages(target_id):
    current_user_id = session.get("user_id")
    role = session.get("role", "client")

    # Client-side pages use /api/messages/0 as a convenient "my thread" alias.
    # Resolve it before the ownership check so clients can load their own chat.
    if role.lower() != "admin" and target_id == 0:
        target_id = current_user_id
    
    # Non-admins can only write/read from their own ID thread
    if role.lower() != "admin" and target_id != current_user_id:
        logger.warning(f"IDOR Threat Alert: Non-admin {current_user_id} attempted reading message thread of {target_id}")
        return jsonify({"error": "Access denied"}), 403

    if request.method == "GET":
        msgs = Message.query.filter_by(client_id=target_id).order_by(Message.timestamp.asc()).all()
        return jsonify([
            {
                "id": m.id,
                "client_id": m.client_id,
                "from": m.from_role,
                "from_role": m.from_role,
                "sender": m.from_role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
                "type": m.type,
                "payment_data": m.payment_data
            } for m in msgs
        ])

    # Handle both JSON and multipart/form-data requests
    uploaded_files = []
    if request.content_type and 'multipart/form-data' in request.content_type:
        content = sanitize_input(request.form.get("content", ""))
        uploaded_files = request.files.getlist('files')
    else:
        data = request.json or {}
        content = sanitize_input(data.get("content", ""))
    
    if not content:
        return jsonify({"error": "No content"}), 400

    msg = Message(
        client_id=target_id,
        from_role="admin" if role.lower() == "admin" else "client",
        content=content,
        timestamp=datetime.now(timezone.utc)
    )
    db.session.add(msg)
    db.session.flush()

    # Handle file attachments
    if uploaded_files:
        for file in uploaded_files:
            if file and file.filename and allowed_file(file.filename):
                # Generate secure filename
                original_filename = secure_filename(file.filename)
                # Add timestamp to prevent collisions
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                random_suffix = secrets.token_hex(4)
                stored_filename = f"{timestamp}_{random_suffix}_{original_filename}"
                
                # Save file to uploads directory
                file_path = UPLOADS_DIR / stored_filename
                try:
                    file.save(str(file_path))
                    
                    # Create file attachment record
                    attachment = FileAttachment(
                        message_id=msg.id,
                        client_id=target_id,
                        original_filename=original_filename,
                        stored_filename=stored_filename,
                        file_size=file.content_length,
                        mime_type=file.content_type,
                        uploaded_by_role="admin" if role.lower() == "admin" else "client"
                    )
                    db.session.add(attachment)
                except Exception as e:
                    logger.error(f"Failed to save file {original_filename}: {str(e)}")
                    continue

    db.session.commit()

    return jsonify({
        "status": "success",
        "message": {
            "id": msg.id,
            "client_id": msg.client_id,
            "from": msg.from_role,
            "from_role": msg.from_role,
            "sender": msg.from_role,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
            "type": msg.type,
            "payment_data": msg.payment_data
        }
    })

@app.route("/api/feedback", methods=["GET", "POST"])
def api_feedback():
    if request.method == "GET":
        try:
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 20, type=int), 100)
            
            if page < 1 or per_page < 1:
                return jsonify({"error": "Invalid pagination parameters"}), 400
            
            feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
            return jsonify({
                "data": [
                    {
                        "id": f.id,
                        "client_name": f.client_name,
                        "client_email": f.client_email,
                        "service_category": f.service_category,
                        "rating": f.rating,
                        "comment": f.comment,
                        "created_at": f.created_at.isoformat()
                    } for f in feedbacks.items
                ],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": feedbacks.total,
                    "pages": feedbacks.pages
                }
            })
        except Exception as e:
            logger.error(f"Error fetching feedback: {str(e)}")
            return jsonify({"error": "Failed to fetch feedback"}), 500

    data = request.json or {}
    client_name = sanitize_input(data.get("clientName", ""))
    client_email = sanitize_input(data.get("clientEmail", ""))
    service_category = sanitize_input(data.get("serviceCategory", ""))
    rating = data.get("rating")
    comment = sanitize_input(data.get("comment", ""))

    if not client_name:
        return jsonify({"error": "Name is required"}), 400
    
    if not validate_username(client_name):
        return jsonify({"error": "Invalid name format"}), 400

    if not service_category:
        return jsonify({"error": "Service category is required"}), 400
    
    if len(service_category) > 255:
        return jsonify({"error": "Service category too long"}), 400

    if not rating or not validate_rating(int(rating)):
        return jsonify({"error": "Valid rating (1-5) is required"}), 400

    if not comment or len(comment) < 10 or len(comment) > 2000:
        return jsonify({"error": "Comment must be 10-2000 characters"}), 400

    if client_email and not validate_email(client_email):
        return jsonify({"error": "Invalid email format"}), 400
        
    feedback = Feedback(
        client_name=client_name,
        client_email=client_email if client_email else None,
        service_category=service_category,
        rating=int(rating),
        comment=comment,
        created_at=datetime.now(timezone.utc)
    )

    db.session.add(feedback)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Feedback submitted successfully",
        "feedback": {
            "id": feedback.id,
            "client_name": feedback.client_name,
            "service_category": feedback.service_category,
            "rating": feedback.rating,
            "comment": feedback.comment,
            "created_at": feedback.created_at.isoformat()
        }
    })

# --- SECURE FILE MANAGEMENT ENDPOINTS ---

@app.route("/api/messages/<int:message_id>/upload", methods=["POST"])
@login_required
def upload_file(message_id):
    try:
        msg = Message.query.get(message_id)
        if not msg:
            return jsonify({"error": "Message not found"}), 404
        
        # Guard ownership context
        role = session.get("role", "client")
        current_user_id = session.get("user_id")
        if role.lower() != "admin" and msg.client_id != current_user_id:
            logger.warning(f"Unauthorized upload attempt by {current_user_id} on thread belonging to {msg.client_id}")
            return jsonify({"error": "Access denied"}), 403
        
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "File type not allowed"}), 400

        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({"error": "File exceeds 100MB limit"}), 413
        
        if file_size == 0:
            return jsonify({"error": "File is empty"}), 400
        
        original_filename = secure_filename(file.filename)
        unique_filename = f"{secrets.token_hex(16)}_{original_filename}"
        
        # Retrieve safe verified path free of path-traversal payloads
        filepath = get_safe_file_path(unique_filename)
        
        # Write to secure directory path
        file.save(filepath)
        
        attachment = FileAttachment(
            message_id=message_id,
            client_id=msg.client_id,
            original_filename=original_filename,
            stored_filename=unique_filename,
            file_size=file_size,
            mime_type=file.content_type or 'application/octet-stream',
            uploaded_by_role="admin" if role.lower() == "admin" else "client"
        )
        
        db.session.add(attachment)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "file_id": attachment.id,
            "filename": original_filename,
            "size": file_size
        })
    
    except Exception as e:
        logger.error(f"File upload processing error: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Failed to upload file"}), 500

@app.route("/api/files/<int:file_id>/download")
@login_required
def download_file(file_id):
    try:
        attachment = FileAttachment.query.get(file_id)
        if not attachment:
            return jsonify({"error": "File not found"}), 404        
        # Check permissions context
        role = session.get("role", "client")
        current_user_id = session.get("user_id")
        if role.lower() != "admin" and attachment.client_id != current_user_id:
            logger.warning(f"Unauthorized file access block: User {current_user_id} tried downloading file {file_id}")
            return jsonify({"error": "Access denied"}), 403
        
        # Strictly path traversal-hardened file pointer
        filepath = get_safe_file_path(attachment.stored_filename)
        
        if not filepath.exists():
            logger.error(f"Target stored file does not exist on disk: {filepath}")
            return jsonify({"error": "File not found on server"}), 404
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=attachment.original_filename,
            mimetype=attachment.mime_type
        )
    
    except Exception as e:
        logger.error(f"File download processing error: {str(e)}")
        return jsonify({"error": "Failed to download file"}), 500

@app.route("/api/messages/<int:target_id>/files")
@login_required
def get_message_files(target_id):
    try:
        role = session.get("role", "client")
        current_user_id = session.get("user_id")

        if role.lower() != "admin" and target_id == 0:
            target_id = current_user_id
        
        if role.lower() != "admin" and target_id != current_user_id:
            return jsonify({"error": "Access denied"}), 403
        
        files = FileAttachment.query.filter_by(client_id=target_id).order_by(FileAttachment.uploaded_at.desc()).all()
        
        return jsonify({
            "files": [
                {
                    "id": f.id,
                    "message_id": f.message_id,
                    "original_filename": f.original_filename,
                    "file_size": f.file_size,
                    "mime_type": f.mime_type,
                    "uploaded_by": f.uploaded_by_role,
                    "uploaded_at": f.uploaded_at.isoformat()
                } for f in files
            ]
        })
    
    except Exception as e:
        logger.error(f"Error fetching message attachment catalog: {str(e)}")
        return jsonify({"error": "Failed to fetch files"}), 500

@app.route("/api/files/<int:file_id>", methods=["DELETE"])
@login_required
def delete_file(file_id):
    try:
        attachment = FileAttachment.query.get(file_id)
        if not attachment:
            return jsonify({"error": "File not found"}), 404
        
        role = session.get("role", "client")
        current_user_id = session.get("user_id")
        
        # Only admin or the direct uploader can initiate deletions
        is_uploader = (attachment.uploaded_by_role == "client" and attachment.client_id == current_user_id)
        if role.lower() != "admin" and not is_uploader:
            return jsonify({"error": "Cannot delete this file"}), 403
        
        # Verify and secure local storage pointer
        filepath = get_safe_file_path(attachment.stored_filename)
        if filepath.exists():
            filepath.unlink() # Secure file removal
        
        db.session.delete(attachment)
        db.session.commit()
        
        logger.info(f"File deleted: {attachment.original_filename}")
        return jsonify({"status": "success", "message": "File deleted"})
    
    except Exception as e:
        logger.error(f"File deletion error: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Failed to delete file"}), 500

# Initialize Database Schema securely
initialize_database()

# --- SERVER RUN ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    # Never expose debug=True in production settings as it exposes an interactive debugger console
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
