# Personal App - EmmaStudio AI Core

A professional freelancing platform built with Flask and modern web technologies.

## Features

- **Admin Dashboard**: Manage clients, projects, and communications
- **Client Portal**: Service ordering, project tracking, and messaging
- **Real-time Analytics**: Revenue tracking and project status monitoring
- **Secure Authentication**: User login and role-based access control
- **Professional UI**: Futuristic cyberpunk design theme

## Project Structure

```
├── server.py              # Flask application (main entry point)
├── wsgi.py               # WSGI entry point for cloud deployment
├── requirements.txt      # Python dependencies
├── render.yaml          # Render.com deployment config
├── build.sh             # Build script for Render
├── .gitignore           # Git ignore rules
├── .env.example         # Example environment variables
│
├── static/
│   ├── app.js           # Frontend JavaScript
│   └── style.css        # Styles
│
├── templates/
│   ├── base.html        # Base template with navbar
│   ├── index.html       # Admin dashboard
│   ├── login.html       # Login page
│   ├── clients.html     # Clients management
│   ├── projects.html    # Projects management
│   ├── services.html    # Services page
│   ├── client_portal.html    # Client dashboard
│   ├── client_order.html     # Service ordering
│   └── client_base.html      # Client template base
│
└── Data Files (JSON)
    ├── users.json       # User accounts
    ├── clients.json     # Client information
    ├── projects.json    # Projects/orders
    ├── messages.json    # Communication threads
    └── services.json    # Available services
```

## Local Development

### Setup

```bash
# Clone repository
git clone https://github.com/yourusername/personal-app.git
cd personal-app

# Create virtual environment
python -m venv venv
source venv/Scripts/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
copy .env.example .env
# Edit .env and set FLASK_SECRET_KEY
```

### Run

```bash
# Development mode (debug enabled)
set FLASK_ENV=development
python server.py
```

Visit `http://localhost:5000`

### Default Test Credentials

After first run, a default admin user is created:
- **Username**: admin
- **Password**: admin123 (first user registered becomes admin)

## API Endpoints

### Authentication
- `GET /login` - Login page
- `POST /login` - Process login
- `POST /register` - Register new user
- `GET /logout` - Logout

### Admin Routes
- `GET /` - Admin dashboard
- `GET /clients` - Clients management
- `GET /projects` - Projects management
- `GET /services` - Services page

### Client Routes
- `GET /client/dashboard` - Client portal
- `GET /client/order` - Service ordering form

### API Routes
- `GET /api/dashboard` - Dashboard data (JSON)
- `GET /api/projects` - Get projects list
- `POST /api/projects` - Create new project
- `POST /api/projects/<id>/payment` - Record payment
- `GET /api/messages/<client_id>` - Get messages
- `POST /api/messages/<client_id>` - Send message
- `GET /api/services` - Get services list
- `GET /api/profile` - Get profile information

## Deployment

### Render.com (Recommended for Free Tier)

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for step-by-step instructions.

**Quick Start**:
```bash
git push origin main  # Deploy automatically to Render
```

### Other Platforms

- **Heroku**: Use `Procfile` (similar to render.yaml)
- **PythonAnywhere**: Upload files and configure wsgi.py
- **Railway**: Connect GitHub repo
- **Replit**: Create new project from GitHub repo

## Technology Stack

- **Backend**: Flask 3.0.0 (Python)
- **Server**: Gunicorn (production WSGI server)
- **Frontend**: Vanilla JavaScript + CSS3
- **Data**: JSON (local development) / PostgreSQL (production recommended)
- **Charts**: Chart.js
- **Icons**: Font Awesome 6
- **Fonts**: Google Fonts (Rajdhani, Inter)

## Security Notes

⚠️ **IMPORTANT FOR PRODUCTION**:

1. Change the `FLASK_SECRET_KEY` environment variable
2. Use HTTPS only (Render provides this by default)
3. Implement password hashing properly (currently SHA256, upgrade to bcrypt)
4. Migrate from JSON to database
5. Add CSRF protection to forms
6. Implement rate limiting
7. Add input validation and sanitization

## Database Migration Path

Current app uses JSON files. For production:

1. **Set up PostgreSQL database**
2. **Add SQLAlchemy ORM**
3. **Create database models**
4. **Migrate data** from JSON to database
5. **Update routes** to use ORM

Required packages:
```
flask-sqlalchemy==3.1.1
psycopg2-binary==2.9.9
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is proprietary. All rights reserved.

## Contact

- **Developer**: Emmanuel Ugwu
- **Email**: your-email@example.com
- **Portfolio**: [Your Website]

---

**Status**: ✅ Ready for Deployment
**Last Updated**: 2026-04-04
