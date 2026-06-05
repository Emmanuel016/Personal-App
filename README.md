# Personal App - EmmaStudio AI Core

A professional freelancing platform built with Flask and modern web technologies.

## Features

- **Admin Dashboard**: Manage clients, projects, and communications
- **Client Portal**: Service ordering, project tracking, and messaging
- **Real-time Analytics**: Revenue tracking and project status monitoring
- **Secure Authentication**: User login and role-based access control
- **Professional UI**: Futuristic cyberpunk design theme
- **File Upload System**: Upload and share files in messaging (admin & client)
- **PayPal Integration**: Secure payment processing for project invoices
- **Advanced Messaging**: Real-time communication with file attachments
- **Project Management**: Track project status, deadlines, and payments

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
│   ├── feedback.html    # Feedback page for clients
│   ├── client_portal.html    # Client dashboard
│   ├── client_order.html     # Service ordering
│   ├── client_billing.html   # Client billing & payments
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
- `GET /client/billing` - Client billing and payments

### API Routes
- `GET /api/dashboard` - Dashboard data (JSON)
- `GET /api/projects` - Get projects list
- `POST /api/projects` - Create new project
- `POST /api/projects/<id>/payment` - Record payment
- `GET /api/messages/<client_id>` - Get messages
- `POST /api/messages/<client_id>` - Send message
- `GET /api/services` - Get services list
- `GET /api/profile` - Get profile information

### File Upload API
- `POST /api/messages/<message_id>/upload` - Upload file to message
- `GET /api/files/<file_id>/download` - Download file attachment
- `GET /api/files/<target_id>/list` - List files for message thread
- `DELETE /api/files/<file_id>` - Delete file attachment

### PayPal Integration API
- `POST /api/paypal/create-order` - Create PayPal payment order
- `POST /api/paypal/capture-order` - Capture PayPal payment
- `GET /api/paypal/checkout/<project_id>` - Get PayPal checkout URL

## Deployment

### Render.com (Recommended for Free Tier)

#### Quick Setup

1. **Create a Render Account**
   - Visit [render.com](https://render.com) and sign up for a free account
   - Connect your GitHub repository

2. **Configure Environment Variables**
   In your Render dashboard, set these environment variables:
   ```
   FLASK_SECRET_KEY=your-secret-key-here
   DATABASE_URL=postgresql://user:password@host:port/database
   FLASK_ENV=production
   ```

3. **Deploy**
   ```bash
   git push origin main  # Deploy automatically to Render
   ```

#### Detailed Configuration

**Build Command:**
```bash
./build.sh
```

**Start Command:**
```bash
./start.sh
```

**Environment Variables:**
- `FLASK_SECRET_KEY` - Required for session security (generate a random string)
- `DATABASE_URL` - PostgreSQL connection string (Render provides this automatically)
- `FLASK_ENV` - Set to `production`
- `PORT` - Render sets this automatically (default: 8000)

#### File Upload Configuration

The app uses an `uploads` directory for file attachments. Render provides ephemeral storage, so:
- Files are stored temporarily during the session
- For persistent storage, consider using Render's disk or cloud storage (S3, etc.)

#### Performance Optimization

The deployment is optimized for Render's free tier:
- **2 Gunicorn workers** - Balances performance and memory limits
- **120 second timeout** - Handles longer requests
- **Worker recycling** - Prevents memory leaks
- **Shared memory for temp files** - Faster I/O operations

#### Monitoring

Render provides built-in monitoring:
- **Logs** - View application logs in Render dashboard
- **Metrics** - CPU, memory, and response time
- **Alerts** - Set up notifications for errors or downtime

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed troubleshooting.

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
- **Database ORM**: SQLAlchemy 2.0.23
- **Authentication**: bcrypt 4.1.2
- **Rate Limiting**: Flask-Limiter 3.5.0
- **Session Management**: Flask-Session 0.5.0
- **Charts**: Chart.js
- **Icons**: Font Awesome 6
- **Fonts**: Google Fonts (Rajdhani, Inter)
- **Payments**: PayPal REST API SDK

## Security Notes

⚠️ **IMPORTANT FOR PRODUCTION**:

1. Change the `FLASK_SECRET_KEY` environment variable
2. Use HTTPS only (Render provides this by default)
3. Implement password hashing properly (bcrypt is now included)
4. Migrate from JSON to database (SQLAlchemy is now included)
5. Add CSRF protection to forms
6. Implement rate limiting (Flask-Limiter is now included)
7. Add input validation and sanitization
8. Configure PayPal API credentials securely (use environment variables)
9. Implement file upload security (validate file types, sizes, and scan for malware)
10. Set up proper file storage permissions

## Database Migration Path

Current app uses JSON files. For production:

1. **Set up PostgreSQL database**
2. **Add SQLAlchemy ORM** (already included in requirements.txt)
3. **Create database models**
4. **Migrate data** from JSON to database
5. **Update routes** to use ORM

Required packages (already included):
```
flask-sqlalchemy==3.1.1
psycopg2-binary==2.9.10
SQLAlchemy==2.0.23
```

## New Features Overview

### File Upload System

The application now supports file uploads in messaging for both admin and client portals:

- **Upload Limit**: 100MB maximum file size
- **Supported File Types**: Configurable in server.py
- **Storage**: Files stored in `uploads/` directory
- **Database**: File metadata stored in `FileAttachment` model
- **UI**: Green "UPLOAD FILE" button in messaging interface
- **Download**: Files can be downloaded via API endpoint

**Usage**:
1. Click the green "UPLOAD FILE" button in the messaging interface
2. Select a file from your device
3. The file is automatically attached to a new message
4. Recipients can download the file directly from the chat

### PayPal Integration

Secure payment processing for project invoices:

- **Payment Flow**: Create order → Capture payment → Update project status
- **Security**: PayPal REST API with secure credential management
- **Client Portal**: Clients can pay invoices directly from billing page
- **Admin Dashboard**: Track payment status and project updates
- **Environment Variables**: Required for PayPal API credentials

**Required Environment Variables**:
```
PAYPAL_CLIENT_ID=your-paypal-client-id
PAYPAL_CLIENT_SECRET=your-paypal-client-secret
PAYPAL_MODE=sandbox  # or 'live' for production
```

### Advanced Messaging

Enhanced communication features:

- **Real-time Messages**: Instant message delivery
- **File Attachments**: Share documents, images, and files
- **Message History**: Complete conversation tracking
- **Role-based Access**: Admin and client messaging separation
- **File Download**: Secure file download with access control

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
