import os
import hashlib
from datetime import datetime, date
from flask import (
    Flask, jsonify, request, render_template,
    redirect, session
)
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "CHIDIOGOEZE042")

# --- DATABASE CONFIG ---
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:password@localhost:5432/personalapp")

# Try PostgreSQL first, fallback to SQLite for local development
try:
    import psycopg2
    # Add SSL configuration for Render PostgreSQL if needed
    if "render.com" in DATABASE_URL and "sslmode" not in DATABASE_URL:
        DATABASE_URL += "?sslmode=require"
    
    # Test PostgreSQL connection
    conn = psycopg2.connect(DATABASE_URL)
    conn.close()
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    print("[*] Using PostgreSQL database")
except (psycopg2.OperationalError, ImportError) as e:
    # Fallback to SQLite for local development
    sqlite_db = "personalapp.db"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{sqlite_db}"
    print(f"[*] PostgreSQL not available ({e}), using SQLite database: {sqlite_db}")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# --- MODELS ---

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=True)  # nullable for record_only
    role = db.Column(db.String(50), default="client")
    email = db.Column(db.String(255))
    company = db.Column(db.String(255))
    type = db.Column(db.String(50))  # e.g. "record_only"
    date_added = db.Column(db.Date)

    projects = db.relationship("Project", backref="client", lazy=True)
    messages = db.relationship("Message", backref="client_user", lazy=True)

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
    deadline = db.Column(db.Date)  # Add missing deadline field
    amount_paid = db.Column(db.Float, default=0.0)
    price = db.Column(db.Float, default=0.0)

class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    from_role = db.Column("from", db.String(50))  # "admin" or "client"
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- SAFE DATABASE INITIALIZATION ---

def initialize_database():
    """Create database tables if they don't exist"""
    try:
        print("[*] Creating database tables...")
        
        # Force import all models to ensure they're registered
        from sqlalchemy import inspect, text
        
        with app.app_context():
            # Check if deadline column exists in projects table
            engine = db.engine
            inspector = inspect(engine)
            
            # Create all tables first
            print("[*] Creating tables...")
            db.create_all()
            
            # Check if projects table exists and has deadline column
            if 'projects' in inspector.get_table_names():
                columns = [col['name'] for col in inspector.get_columns('projects')]
                print(f"[*] Current projects table columns: {columns}")
                
                # Add deadline column if it doesn't exist
                if 'deadline' not in columns:
                    print("[*] Adding deadline column to projects table...")
                    try:
                        with engine.connect() as conn:
                            conn.execute(text("ALTER TABLE projects ADD COLUMN deadline DATE"))
                            conn.commit()
                        print("[*] Successfully added deadline column")
                    except Exception as e:
                        print(f"[!] Error adding deadline column: {str(e)}")
                        # Try SQLite specific syntax
                        try:
                            with engine.connect() as conn:
                                conn.execute(text("ALTER TABLE projects ADD COLUMN deadline DATE"))
                                conn.commit()
                            print("[*] Successfully added deadline column (SQLite)")
                        except Exception as e2:
                            print(f"[!] Still failed to add deadline column: {str(e2)}")
            # Verify tables exist
            tables = inspector.get_table_names()
            print(f"[*] Available tables: {tables}")
            
            if not tables:
                print("[!] No tables created - forcing manual table creation...")
                # Manual table creation as fallback
                User.__table__.create(engine, checkfirst=True)
                Project.__table__.create(engine, checkfirst=True)
                Message.__table__.create(engine, checkfirst=True)
                Service.__table__.create(engine, checkfirst=True)
                
                # Check again
                tables = inspector.get_table_names()
                print(f"[*] Tables after manual creation: {tables}")
            
            print("[*] Database initialization completed successfully")
            
    except Exception as e:
        print(f"[!] Database initialization error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

# --- UTILS ---

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def require_login():
    return "user" in session

def is_admin():
    return session.get("role") == "admin"

def get_next_id(model):
    last = db.session.query(db.func.max(model.id)).scalar()
    return (last or 0) + 1

@app.route("/")
def dashboard():
    if not require_login():
        return redirect("/register")

    if is_admin():
        users = User.query.all()
        clients = [u for u in users if (u.role or "").lower() == "client"]
        projects = Project.query.all()
        return render_template("index.html", clients=len(clients), projects=len(projects))
    else:
        return redirect("/client/dashboard")


@app.route("/login", methods=["GET", "POST"])
def login():
    try:
        if request.method == "GET":
            return render_template("login.html")

        username = request.form.get("username")
        password = hash_password(request.form.get("password", ""))

        if not username or not password:
            return render_template("login.html", error="Username and password are required")

        user = User.query.filter(
            (User.username == username) & (User.password == password)
        ).first()
        
        if user:
            session["user"] = user.username
            session["user_id"] = user.id
            session["role"] = user.role or "client"
            return redirect("/")

        return render_template("login.html", error="Invalid credentials")
    except Exception as e:
        print(f"Login error: {str(e)}")
        db.session.rollback()
        return render_template("login.html", error="An error occurred during login")

@app.route("/register", methods=["GET", "POST"])
def register():
    try:
        if request.method == "GET":
            return render_template("login.html", register=True)

        username = request.form.get("username")
        password = hash_password(request.form.get("password", ""))

        if not username or not password:
            return render_template("login.html", register=True, error="Username and password are required")

        existing = User.query.filter(
            db.func.lower(User.username) == username.lower()
        ).first()
        if existing:
            return render_template("login.html", register=True, error="User already exists")

        try:
            total_users = User.query.count()
        except Exception as count_error:
            print(f"User count error: {str(count_error)}")
            total_users = 0
        
        role = "admin" if total_users == 0 else "client"

        new_user = User(
            username=username,
            password=password,
            role=role,
            date_added=date.today()
        )
        
        db.session.add(new_user)
        db.session.flush()
        
        session["user"] = new_user.username
        session["user_id"] = new_user.id
        session["role"] = new_user.role
        
        db.session.commit()
        return redirect("/")
    except Exception as e:
        print(f"Register error: {str(e)}")
        db.session.rollback()
        return render_template("login.html", register=True, error="An error occurred during registration")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# --- CLIENT PORTAL ---

@app.route("/client/dashboard")
def client_portal():
    if not require_login():
        return redirect("/login")
    return render_template("client_portal.html")

@app.route("/api/services")
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
def services_page():
    if not require_login():
        return redirect("/login")
    services = Service.query.all()
    return render_template("services.html", services=services)

@app.route("/client_billing")
def client_billing():
    if not require_login():
        return redirect("/login")
    return render_template("client_billing.html")

@app.route("/client/order")
def order_page():
    if not require_login():
        return redirect("/login")
    return render_template("client_order.html")

@app.route("/client_feedback")
def client_feedback():
    if not require_login():
        return redirect("/login")  
    return render_template("client_feedback.html")

@app.route("/api/orders", methods=["POST"])
def place_order():
    if not require_login():
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json or {}
    service_name = data.get("service_name")
    description = data.get("description")
    budget = data.get("budget")
    price = float(data.get("price", 0))

    new_project = Project(
        client_user_id=session.get("user_id"),
        client_name=session.get("user"),
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
        f"💼 NEW ORDER: Client '{session.get('user')}' placed order for "
        f"'{service_name}' | Est. Price: £{price:.2f} | Status: Awaiting Review"
    )
    msg = Message(
        client_id=session.get("user_id"),
        from_role="client",
        content=content,
        timestamp=datetime.utcnow()
    )
    db.session.add(msg)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Order transmitted successfully. Emmanuel will review and get back to you shortly."
    })

@app.route("/api/profile")
def get_profile():
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
def clients_page():
    if not require_login() or not is_admin():
        return redirect("/")
    return render_template("clients.html")


@app.route("/projects")
def projects_page():
    if not require_login():
        return redirect("/login")
    return render_template("projects.html")


# --- API: DASHBOARD DATA ---

@app.route("/api/dashboard")
def dashboard_data():
    if not require_login():
        return jsonify({"error": "Unauthorized"}), 403

    if is_admin():
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
def get_clients():
    if not require_login() or not is_admin():
        return jsonify({"error": "Unauthorized"}), 403

    users = User.query.all()
    clients = [u for u in users if (u.role or "").lower() == "client"]

    return jsonify([
        {
            "id": c.id,
            "username": c.username,
            "email": c.email,
            "company": c.company,
            "role": c.role,
            "type": c.type,
            "date_added": c.date_added.isoformat() if c.date_added else None
        } for c in clients
    ])


# --- API: PROJECTS ---

@app.route("/api/test")
def test_connection():
    """Test endpoint to verify database connection and authentication"""
    try:
        # Test database connection
        project_count = Project.query.count()
        user_count = User.query.count()
        
        return jsonify({
            "status": "success",
            "database_connected": True,
            "projects_count": project_count,
            "users_count": user_count,
            "session": {
                "user": session.get("user"),
                "user_id": session.get("user_id"),
                "role": session.get("role"),
                "logged_in": require_login()
            }
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "database_connected": False,
            "error": str(e)
        }), 500

@app.route("/api/projects")
def get_projects():
    print(f"[DEBUG] Projects API called - Session: {session}")
    print(f"[DEBUG] User logged in: {require_login()}")
    print(f"[DEBUG] Is admin: {is_admin()}")
    
    if not require_login():
        print(f"[DEBUG] Unauthorized access attempt")
        return jsonify({"error": "Unauthorized"}), 403
    try:
        # Enhanced query with eager loading for better performance
        if is_admin():
            projects = Project.query.order_by(Project.date_created.desc()).all()
            print(f"[*] Admin requesting projects - found {len(projects)} total projects")
        else:
            uid = session.get("user_id")
            print(f"[*] Client {uid} requesting projects")
            if not uid:
                print(f"[DEBUG] No user_id in session")
                return jsonify({"error": "No user session found"}), 401
            
            projects = Project.query.filter_by(client_user_id=uid).order_by(Project.date_created.desc()).all()
            print(f"[*] Client {uid} requesting projects - found {len(projects)} projects")

        # Enhanced project data with calculated fields
        projects_data = []
        for p in projects:
            project_data = {
                "id": p.id,
                "client_user_id": p.client_user_id,
                "client_name": p.client_name,
                "title": p.title,
                "desc": p.desc,
                "budget_estimate": p.budget_estimate,
                "status": p.status,
                "date_created": p.date_created.isoformat() if p.date_created else None,
                "deadline": p.deadline.isoformat() if p.deadline else None,
                "amount_paid": float(p.amount_paid or 0),
                "price": float(p.price or 0),
                "outstanding_balance": float(p.price or 0) - float(p.amount_paid or 0),
                "is_client_project": bool(p.client_user_id and p.client_name),
                "days_until_deadline": None
            }
            
            # Calculate days until deadline
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
            
            # Detailed logging for admin
            if is_admin():
                print(f"    - Project {p.id}: '{p.title}' by {p.client_name} (Status: {p.status}, Value: £{p.price})")

        print(f"[*] Successfully processed {len(projects_data)} projects for {session.get('role', 'unknown')}")
        
        return jsonify(projects_data)
        
    except Exception as e:
        print(f"[!] Error in /api/projects: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to load projects", "details": str(e)}), 500

@app.route("/api/projects", methods=["POST"])
def create_project():
    """Create a new project"""
    if not require_login():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        data = request.json or {}
        
        # Validate required fields
        if not data.get("title"):
            return jsonify({"error": "Project title is required"}), 400
        
        # Get client info
        if is_admin():
            client_id = data.get("client_user_id")
            client_name = data.get("client_name", "Admin Created")
        else:
            client_id = session.get("user_id")
            client_name = session.get("user", "Client")
        
        # Parse deadline if provided
        deadline = None
        if data.get("deadline"):
            try:
                deadline = datetime.strptime(data.get("deadline"), "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"error": "Invalid deadline format. Use YYYY-MM-DD"}), 400
        
        # Create new project
        new_project = Project(
            client_user_id=client_id,
            client_name=client_name,
            title=data.get("title"),
            desc=data.get("desc", ""),
            budget_estimate=data.get("budget_estimate", ""),
            status=data.get("status", "Pending Approval"),
            deadline=deadline,
            price=float(data.get("price", 0.0))
        )
        
        db.session.add(new_project)
        db.session.commit()
        
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
        print(f"Error creating project: {str(e)}")
        return jsonify({"error": "Failed to create project", "details": str(e)}), 500

@app.route("/api/projects/<int:project_id>", methods=["PATCH"])
def update_project(project_id):
    """Update project status and payment"""
    if not require_login() or not is_admin():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        data = request.json or {}
        
        # Update status if provided
        if data.get("status"):
            project.status = data["status"]
            print(f"[*] Updated project {project_id} status to: {data['status']}")
        
        # Update payment if provided
        if data.get("amount_paid") is not None:
            project.amount_paid = float(data["amount_paid"])
            print(f"[*] Updated project {project_id} payment to: {data['amount_paid']}")
        
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
        print(f"[!] Error updating project {project_id}: {str(e)}")
        return jsonify({"error": "Failed to update project", "details": str(e)}), 500

@app.route("/api/projects/<int:project_id>/payment", methods=["POST"])
def update_payment(project_id):
    if not require_login() or not is_admin():
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json or {}
    amount = float(data.get("amount", 0))

    project = Project.query.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    project.amount_paid = float(project.amount_paid or 0) + amount
    db.session.commit()

    return jsonify({"status": "success"})

@app.route("/api/projects/<int:project_id>", methods=["DELETE"])
def delete_project(project_id):
    """Delete a project (admin only)"""
    if not require_login() or not is_admin():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        print(f"[*] Admin {session.get('user')} deleting project {project_id}: '{project.title}'")
        
        # Delete the project
        db.session.delete(project)
        db.session.commit()
        
        print(f"[*] Successfully deleted project {project_id}")
        
        return jsonify({
            "status": "success",
            "message": f"Project '{project.title}' deleted successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"[!] Error deleting project {project_id}: {str(e)}")
        return jsonify({"error": "Failed to delete project", "details": str(e)}), 500
# --- API: CLIENT PAYMENT SUBMISSION ---

@app.route("/api/payment/submit", methods=["POST"])
def submit_payment():
    if not require_login():
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json or {}
    project_id = data.get("project_id")
    amount = data.get("amount")
    payment_method = data.get("payment_method", "Bank Transfer")

    if not project_id or not amount:
        return jsonify({"error": "Missing project_id or amount"}), 400

    try:
        amount = float(amount)
        project_id = int(project_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount or project_id"}), 400

    if amount <= 0:
        return jsonify({"error": "Amount must be greater than 0"}), 400

    project = Project.query.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    if project.client_user_id != session.get("user_id"):
        return jsonify({"error": "Unauthorized - Project does not belong to client"}), 403

    old_paid = float(project.amount_paid or 0)
    project.amount_paid = old_paid + amount

    outstanding = max(float(project.price or 0) - project.amount_paid, 0)

    payment_message = Message(
        client_id=session.get("user_id"),
        from_role="client",
        content=(
            f"💳 PAYMENT SENT: Client '{session.get('user')}' submitted payment of £{amount:.2f} "
            f"for project '{project.title}' (ID: {project_id}) via {payment_method}. "
            f"Amount paid updated from £{old_paid:.2f} to £{project.amount_paid:.2f}. "
            f"Outstanding balance: £{outstanding:.2f}."
        ),
        timestamp=datetime.utcnow(),
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

# --- API: ADMIN ADD CLIENT RECORD ---

@app.route("/api/clients/add", methods=["POST"])
def admin_add_client_record():
    if not require_login() or not is_admin():
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json or {}
    username = data.get("username")
    email = data.get("email", "N/A")
    company = data.get("company", "N/A")
    role = data.get("role", "Client")

    if not username:
        return jsonify({"error": "Name/Username required"}), 400

    existing = User.query.filter(db.func.lower(User.username) == username.lower()).first()
    if existing:
        return jsonify({"error": "This record already exists"}), 400

    new_user = User(
        username=username,
        email=email,
        company=company,
        role=role,
        type="record_only",
        date_added=date.today()
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": f"Client record for {username} created.",
        "user": {"id": new_user.id, "name": username}
    })

# --- API: MESSAGES THREAD ---

@app.route("/api/messages/<int:target_id>", methods=["GET", "POST"])
def api_messages(target_id):
    if not require_login():
        return jsonify({"error": "Unauthorized"}), 403

    thread_owner_id = target_id if is_admin() else session.get("user_id")

    if request.method == "GET":
        msgs = Message.query.filter_by(client_id=thread_owner_id).order_by(Message.timestamp.asc()).all()
        return jsonify([
            {
                "id": m.id,
                "client_id": m.client_id,
                "from": m.from_role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
                "type": m.type,
                "payment_data": m.payment_data
            } for m in msgs
        ])

    data = request.json or {}
    content = data.get("content", "").strip()
    if not content:
        return jsonify({"error": "No content"}), 400

    msg = Message(
        client_id=thread_owner_id,
        from_role="admin" if is_admin() else "client",
        content=content,
        timestamp=datetime.utcnow()
    )
    db.session.add(msg)
    db.session.commit()

    return jsonify({"status": "success"})

@app.route("/api/feedback", methods=["GET", "POST"])
def api_feedback():
    if request.method == "GET":
        feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).limit(20).all()
        return jsonify([
            {
                "id": f.id,
                "client_name": f.client_name,
                "client_email": f.client_email,
                "service_category": f.service_category,
                "rating": f.rating,
                "comment": f.comment,
                "created_at": f.created_at.isoformat()
            } for f in feedbacks
        ])

    data = request.json or {}
    client_name = data.get("clientName", "").strip()
    client_email = data.get("clientEmail", "").strip()
    service_category = data.get("serviceCategory", "").strip()
    rating = data.get("rating")
    comment = data.get("comment", "").strip()

    if not client_name:
        return jsonify({"error": "Name is required"}), 400

    if not service_category:
        return jsonify({"error": "Service category is required"}), 400

    if not rating or not (1 <= int(rating) <= 5):
        return jsonify({"error": "Valid rating (1-5) is required"}), 400

    if not comment:
        return jsonify({"error": "Comment is required"}), 400

    feedback = Feedback(
        client_name=client_name,
        client_email=client_email if client_email else None,
        service_category=service_category,
        rating=int(rating),
        comment=comment,
        created_at=datetime.utcnow()
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

# Initialize database after all models are defined (safe, non-destructive)
initialize_database()

# --- SERVER EXECUTION ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
