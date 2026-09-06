# EmmaStudio Personal App

A Flask-powered freelance business management website for EmmaStudio. The application combines an admin command center, a client portal, service ordering, project tracking, messaging with file attachments, invoices, notifications, feedback, and PayPal payment workflows in one web app.

## Table of Contents

- [Overview](#overview)
- [Recent Updates](#recent-updates)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Running Locally](#running-locally)
- [Application Pages](#application-pages)
- [API Overview](#api-overview)
- [Database Models](#database-models)
- [File Uploads](#file-uploads)
- [Invoices and Payments](#invoices-and-payments)
- [Notifications](#notifications)
- [Deployment](#deployment)
- [Security Notes](#security-notes)
- [Troubleshooting](#troubleshooting)
- [Maintenance Checklist](#maintenance-checklist)

## Overview

EmmaStudio Personal App is designed for managing freelance client work from first contact through delivery and payment. Clients can register, order services, upload files, view project and billing information, receive notifications, and submit feedback. Admin users can manage clients, projects, conversations, attached files, invoices, and payment status from a dashboard-style interface.

The app uses Flask and SQLAlchemy for the backend, Jinja templates for server-rendered pages, Socket.IO for realtime notifications, Flask-Mail for invoice emails, ReportLab for invoice PDF generation, and PayPal APIs for payments.

## Recent Updates

### File Upload Improvements (August 2026)

- **Fixed timezone comparison errors** - Resolved issues with timezone-naive vs timezone-aware datetime comparisons in password reset and file upload functions
- **Fixed file size calculation** - Corrected file size reporting from `file.tell()` to `file.content_length` for accurate file size tracking
- **Enhanced error handling** - Added comprehensive try-catch blocks with proper logging and database rollback for file upload failures
- **Immediate download links** - File download links now appear immediately after upload without requiring page reload
- **Production file storage** - Configured uploads directory to use persistent disk mount (`/opt/render/project/uploads`) in production environments

### Password Reset Fixes (August 2026)

- **Fixed timezone comparison** - Added proper timezone handling for password reset token expiration checks
- **Fixed redirect issue** - Password reset now properly redirects to login page after successful reset instead of staying on reset URL
- **Enhanced error messages** - Improved error reporting for invalid/expired tokens and user not found scenarios

### Notification System Updates (August 2026)

- **Self-notification prevention** - Users no longer receive notifications when they send their own messages
- **Admin-only notifications** - File upload and message notifications are now only sent to recipients, not senders
- **Improved notification logic** - Refactored notification sending to ensure proper targeting and reduce duplicate notifications

## Key Features

### Admin Experience

- Dashboard command center with clients, projects, and feedback summaries.
- Client management and manual client creation.
- Project management with status, deadline, pricing, amount paid, and outstanding balance.
- Project cards that show the project owner and attached order files.
- Messaging interface for communicating with clients.
- File upload, download, and deletion controls.
- Invoice management, PDF generation, resend, mark-paid, and payment workflows.
- Admin notification center with read/unread state and bulk actions.

### Client Experience

- Client registration and login.
- Client portal dashboard.
- Service ordering flow with optional file attachments.
- Billing page with PayPal payment support.
- Portfolio/services browsing.
- Feedback submission.
- Client notification center.

### Business Workflow

- New service orders automatically create projects.
- Uploaded order files are attached to the order message and surfaced on the projects page.
- Project payment tracking supports partial payments and outstanding balances.
- Invoice generation supports milestone and completion invoices.
- Payment reminders and overdue status checks can run through the scheduler.

## Tech Stack

### Backend

- Python 3.11+
- Flask 3
- Flask-SQLAlchemy
- Flask-SocketIO
- Flask-Limiter
- Flask-Mail
- APScheduler
- ReportLab
- Requests
- bcrypt

### Database

- SQLite for local development by default.
- PostgreSQL supported in production through `DATABASE_URL`.

### Frontend

- Jinja2 templates.
- Vanilla JavaScript.
- Tailwind CDN usage in some templates.
- Font Awesome icons.
- Chart.js for dashboard/project visualizations.

### Deployment

- Gunicorn.
- Render-compatible `render.yaml`, `build.sh`, and `start.sh`.

## Project Structure

```text
.
├── server.py                       # Main Flask application, models, routes, APIs, services
├── wsgi.py                         # Production WSGI entrypoint
├── requirements.txt                # Python dependencies
├── Procfile                        # Gunicorn process definition
├── render.yaml                     # Render deployment configuration
├── build.sh                        # Render build script
├── start.sh                        # Render/startup script
├── .env.example                    # Example environment configuration
├── models.py                       # Houses my database objects
├── templates/
│   ├── base.html                   # Admin base layout
│   ├── client_base.html            # Client base layout
│   ├── index.html                  # Admin dashboard
│   ├── clients.html                # Admin clients page
│   ├── projects.html               # Admin projects page
│   ├── invoices.html               # Invoice management page
│   ├── services.html               # Services/portfolio page
│   ├── client_portal.html          # Client dashboard
│   ├── client_order.html           # Client order form
│   ├── client_billing.html         # Client billing/payment page
│   ├── notifications.html          # Admin notifications
│   └── client_notification.html    # Client notifications
├── static/
│   ├── images/                     # Future Background images
│   ├── app.js                      # Javascript backend logics
│   └── style.css                   # All background styles and Cyberpunk fonts
|   
└── uploads/                        # Runtime upload directory, created 
automatically
```

## Getting Started

### Prerequisites

- Python 3.11 or newer.
- `pip`.
- Optional: PostgreSQL for production-like database testing.
- Optional: PayPal developer account for payment testing.

### 1. Clone or Open the Project

Open the project folder:

```powershell
cd "C:\Users\user\Documents\Personal App"
```

### 2. Create a Virtual Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env` and update values for your local or production environment.

```powershell
Copy-Item .env.example .env
```

For local development, you can leave `DATABASE_URL` empty to use SQLite.

### 5. Start the App

```powershell
python server.py
```

By default, the app runs on:

```text
http://localhost:8000
```

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `FLASK_ENV` | Recommended | Set to `development` locally or `production` when deployed. |
| `FLASK_SECRET_KEY` | Production required | Secret key for Flask sessions. Use a long random value. |
| `ALLOWED_ORIGINS` | Recommended | Comma-separated CORS origins. Use specific domains in production. |
| `DATABASE_URL` | Production required | PostgreSQL connection URL. Empty value falls back to local SQLite. |
| `PAYPAL_MODE` | Optional | `sandbox` or `live`. Defaults to `sandbox`. |
| `PAYPAL_CLIENT_ID` | Optional | PayPal REST API client ID. Required for PayPal payments. |
| `PAYPAL_CLIENT_SECRET` | Optional | PayPal REST API secret. Required for PayPal payments. |
| `MAIL_SERVER` | Optional | SMTP host. Defaults to Gmail SMTP. |
| `MAIL_PORT` | Optional | SMTP port. Defaults to `587`. |
| `MAIL_USE_TLS` | Optional | Enables TLS. Defaults to `True`. |
| `MAIL_USERNAME` | Optional | SMTP username. Required to send invoice emails. |
| `MAIL_PASSWORD` | Optional | SMTP password or app password. |
| `MAIL_DEFAULT_SENDER` | Optional | Default sender email address. |
| `COMPANY_NAME` | Optional | Company name shown on invoices. |
| `COMPANY_ADDRESS` | Optional | Company address shown on invoices. |
| `COMPANY_CITY` | Optional | Company city shown on invoices. |
| `COMPANY_COUNTRY` | Optional | Company country shown on invoices. |
| `COMPANY_PHONE` | Optional | Company phone shown on invoices. |
| `COMPANY_EMAIL` | Optional | Company email shown on invoices. |
| `PAYMENT_METHODS` | Optional | Payment methods text shown in invoice emails. |
| `LATE_FEE` | Optional | Late fee terms shown in invoice emails. |
| `EARLY_DISCOUNT` | Optional | Early discount terms shown in invoice emails. |
| `PORT` | Optional | Server port. Defaults to `8000` in `server.py`. |
| `WORKERS` | Optional | Gunicorn worker count for production. |
| `TIMEOUT` | Optional | Gunicorn timeout in seconds. |
| `HTTPS_ONLY` | Optional | Set to `true` to force secure session cookies. |

## Running Locally

### Development Server

```powershell
python server.py
```

### Production-Style WSGI Run

On platforms that support Gunicorn:

```bash
gunicorn wsgi:app
```

On Windows, use the Flask development server locally. Gunicorn is primarily for Unix-like production environments.

### Database Initialization

Database tables are created automatically during app startup through `initialize_database()`. Local development uses:

```text
instance/personalapp.db
```

or the Flask instance path for SQLite, depending on runtime configuration.

## Application Pages

### Public and Auth

| Route | Purpose |
| --- | --- |
| `/login` | Login page. |
| `/register` | User registration. |
| `/logout` | End current session. |

### Admin Pages

| Route | Purpose |
| --- | --- |
| `/` | Admin dashboard / command center. |
| `/clients` | Client management. |
| `/projects` | Project management with owner details and attached order files. |
| `/invoices` | Invoice management. |
| `/notifications` | Admin notifications. |

### Client Pages

| Route | Purpose |
| --- | --- |
| `/client/dashboard` | Client portal dashboard. |
| `/client/register` | Client registration page. |
| `/client/order` | Service order form with file attachments. |
| `/client_billing` | Client billing and payment page. |
| `/client_feedback` | Client feedback form. |
| `/client/notifications` | Client notification center. |
| `/services` | Service/portfolio page. |

## API Overview

The app exposes JSON APIs for dashboard data, projects, clients, messages, files, payments, feedback, invoices, and notifications.

### Dashboard and Profile

| Endpoint | Methods | Purpose |
| --- | --- | --- |
| `/api/test` | `GET` | Health check and database status. |
| `/api/dashboard` | `GET` | Dashboard statistics. |
| `/api/profile` | `GET` | Current user profile. |
| `/api/services` | `GET` | Available services. |

### Projects

| Endpoint | Methods | Purpose |
| --- | --- | --- |
| `/api/projects` | `GET` | List projects with pagination. |
| `/api/projects` | `POST` | Create a project. |
| `/api/projects/<project_id>` | `PATCH` | Update project fields. |
| `/api/projects/<project_id>` | `DELETE` | Delete a project. |
| `/api/projects/<project_id>/payment` | `POST` | Add a payment to a project. |

### Orders

| Endpoint | Methods | Purpose |
| --- | --- | --- |
| `/api/orders` | `POST` | Place a client service order and upload optional files. |

### Clients and Messages

| Endpoint | Methods | Purpose |
| --- | --- | --- |
| `/api/clients` | `GET` | List clients. |
| `/api/clients/add` | `POST` | Add a client record. |
| `/api/messages/<target_id>` | `GET`, `POST` | Fetch or send messages. |
| `/api/messages/<message_id>/upload` | `POST` | Upload files to an existing message. |
| `/api/messages/<target_id>/files` | `GET` | List files for a client/message context. |

### Files

| Endpoint | Methods | Purpose |
| --- | --- | --- |
| `/api/files/<file_id>/download` | `GET` | Download an uploaded file. |
| `/api/files/<file_id>` | `DELETE` | Delete an uploaded file. |

### Feedback

| Endpoint | Methods | Purpose |
| --- | --- | --- |
| `/api/feedback` | `GET`, `POST` | List or submit feedback. |

### PayPal

| Endpoint | Methods | Purpose |
| --- | --- | --- |
| `/api/paypal/create-payment` | `POST` | Create a PayPal payment. |
| `/api/paypal/execute-payment` | `GET`, `POST` | Execute an approved PayPal payment. |
| `/api/paypal/cancel-payment` | `GET` | Handle cancelled PayPal payments. |

### Invoices

| Endpoint | Methods | Purpose |
| --- | --- | --- |
| `/api/invoices` | `GET` | List invoices. |
| `/api/invoices/generate` | `POST` | Generate an invoice. |
| `/api/invoices/<invoice_id>/pay` | `GET` | Create PayPal checkout for invoice payment. |
| `/api/invoices/<invoice_id>/capture` | `POST` | Capture invoice payment. |
| `/api/invoices/<invoice_id>/pdf` | `GET` | Download invoice PDF. |
| `/api/invoices/<invoice_id>/resend` | `POST` | Resend invoice email. |
| `/api/invoices/<invoice_id>/mark-paid` | `POST` | Mark invoice as paid manually. |

### Notifications

| Endpoint | Methods | Purpose |
| --- | --- | --- |
| `/api/notifications` | `GET` | List current user notifications. |
| `/api/notifications/stats` | `GET` | Notification counts. |
| `/api/notifications/<notification_id>/read` | `POST` | Mark notification as read. |
| `/api/notifications/mark-all-read` | `POST` | Mark all notifications as read. |
| `/api/notifications/<notification_id>` | `DELETE` | Delete a notification. |
| `/api/notifications/delete-read` | `DELETE` | Delete all read notifications. |
| `/api/admin/notifications/*` | Multiple | Admin-specific notification endpoints. |
| `/api/client/notifications/*` | Multiple | Client-specific notification endpoints. |

## Database Models

### User

Stores login identity, role, contact details, company information, and client metadata.

Important fields:

- `username`
- `password`
- `role`
- `email`
- `company`
- `phone`
- `type`
- `date_added`

### Project

Tracks work ordered by clients.

Important fields:

- `client_user_id`
- `client_name`
- `title`
- `desc`
- `budget_estimate`
- `status`
- `date_created`
- `deadline`
- `amount_paid`
- `price`

### Message

Stores admin/client conversation items and payment/order event messages.

Important fields:

- `client_id`
- `from_role`
- `content`
- `timestamp`
- `type`
- `payment_data`

### FileAttachment

Stores metadata for uploaded files. Files are saved on disk in the uploads directory.

Important fields:

- `message_id`
- `client_id`
- `original_filename`
- `stored_filename`
- `file_size`
- `mime_type`
- `uploaded_by_role`
- `uploaded_at`

### Service

Stores services available to clients.

Important fields:

- `name`
- `description`
- `price`
- `icon`

### Feedback

Stores client feedback and ratings.

Important fields:

- `client_name`
- `client_email`
- `service_category`
- `rating`
- `comment`
- `created_at`

### Invoice

Stores invoices, invoice status, due dates, payment status, and line items.

Important fields:

- `project_id`
- `client_id`
- `invoice_number`
- `invoice_type`
- `amount`
- `due_date`
- `status`
- `items`
- `payment_terms`
- `notes`
- `paid_at`

### Notification

Stores realtime and historical notifications.

Important fields:

- `user_id`
- `target_role`
- `type`
- `title`
- `message`
- `data`
- `read`
- `created_at`

## File Uploads

Uploaded files are stored in:

```text
uploads/
```

The application:

- Creates the upload directory automatically.
- Uses secure filenames.
- Adds timestamps and random suffixes to stored filenames.
- Restricts file extensions through `ALLOWED_EXTENSIONS`.
- Enforces a maximum upload size of 100 MB.
- Protects downloads with role and ownership checks.
- Uses safe path resolution to reduce path traversal risk.

Allowed file types include common documents, images, video, audio, archives, source files, and structured data files such as PDF, DOCX, XLSX, PNG, JPG, MP4, ZIP, JSON, CSV, CSS, and Python files.

## Invoices and Payments

The app supports two payment paths:

1. Project payments through PayPal payment endpoints.
2. Invoice payments through PayPal checkout order endpoints.

Invoice features include:

- Milestone and completion invoice generation.
- Automatic invoice numbers.
- Due dates.
- Invoice PDF download.
- Email sending through SMTP.
- Manual mark-as-paid controls.
- Paid, pending, overdue, and cancelled status handling.

To enable PayPal payments, configure:

```text
PAYPAL_MODE=sandbox
PAYPAL_CLIENT_ID=your-client-id
PAYPAL_CLIENT_SECRET=your-client-secret
```

Use `sandbox` while testing. Use `live` only when production credentials and production payment flows are ready.

## Notifications

Notifications are stored in the database and emitted through Socket.IO when possible. The app supports:

- New message notifications.
- Project status notifications.
- Payment notifications.
- Registration/order notifications.
- Admin and client notification centers.
- Read/unread counts.
- Bulk mark-read and delete actions.

## Deployment

The repository includes Render deployment support.

### Render Files

- `render.yaml` defines the web service.
- `build.sh` installs dependencies and prepares runtime directories.
- `start.sh` starts Gunicorn.
- `Procfile` defines a basic Gunicorn process.
- `wsgi.py` exposes the Flask app for production.

### Render Deployment Steps

1. Push the project to a Git repository.
2. Create a new Render web service.
3. Use `render.yaml` or configure manually:
   - Build command: `bash build.sh`
   - Start command: `bash start.sh`
4. Apply the Render blueprint. It defines the web service, upload disk, PostgreSQL database, and production environment variable keys.
5. Fill the `sync: false` variables in the Render dashboard.
6. Keep `PAYPAL_MODE=sandbox` while testing. Change it to `live` only when production PayPal credentials are ready.
7. Confirm persistent disk storage is mounted for uploads.

`render.yaml` declares all environment variables used by the app. Variables marked with `sync: false` must be filled in from the Render dashboard because they are secrets or deployment-specific values:

- `ALLOWED_ORIGINS`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `MAIL_DEFAULT_SENDER`
- `PAYPAL_CLIENT_ID`
- `PAYPAL_CLIENT_SECRET`
- `COMPANY_CITY`
- `COMPANY_COUNTRY`
- `COMPANY_PHONE`
- `COMPANY_EMAIL`

`DATABASE_URL` is provisioned from the Render database named `personal-app-db`, so the app can start with `FLASK_ENV=production`.

The included `render.yaml` mounts a disk at:

```text
/opt/render/project/uploads
```

## Security Notes

This application already includes several important protections:

- Password hashing with bcrypt.
- Session cookie hardening for production/HTTPS environments.
- Login-required route protection.
- Admin-only protection for admin routes.
- Rate limiting with Flask-Limiter.
- Upload filename sanitization.
- Upload path traversal checks.
- File download authorization.
- Payment/project ownership checks on sensitive payment flows.
- CORS origin configuration through `ALLOWED_ORIGINS`.

Production recommendations:

- Set a strong `FLASK_SECRET_KEY`.
- Use PostgreSQL instead of SQLite.
- Set `ALLOWED_ORIGINS` to your actual domain instead of `*`.
- Enable HTTPS.
- Store secrets only in environment variables.
- Do not commit `.env`, upload files, database files, or secret keys.
- Use live PayPal credentials only after full sandbox testing.
- Configure SMTP with an app password or secure provider credentials.

## Troubleshooting

### The app starts but database tables are missing

The app calls `initialize_database()` on startup. If tables are still missing, confirm the configured database is reachable and that `DATABASE_URL` is valid.

### File uploads do not appear

Check:

- The file extension is allowed.
- The file is under 100 MB.
- The `uploads/` directory exists and is writable.
- In production, persistent disk storage is configured.

### Download links return 403

The current user must be an admin or the client who owns the uploaded file.

### PayPal payments fail

Check:

- `PAYPAL_MODE` matches your credentials.
- `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` are set.
- Sandbox accounts are being used for sandbox testing.
- The project or invoice belongs to the current user.

### Invoice emails do not send

Check:

- `MAIL_USERNAME` is configured.
- `MAIL_PASSWORD` is configured.
- SMTP host and port are correct.
- Your mail provider allows SMTP/app-password access.

### Notifications do not update live

Check:

- Browser console for Socket.IO errors.
- `ALLOWED_ORIGINS` includes the site origin.
- The user is logged in and has a valid session.

## Maintenance Checklist

- Review dependencies in `requirements.txt` regularly.
- Rotate secrets if they are exposed.
- Back up the database before production migrations.
- Back up uploaded files if using local or mounted disk storage.
- Keep PayPal credentials separated between sandbox and live.
- Review uploaded file types if client requirements change.
- Monitor application logs for failed payments, failed emails, and upload errors.

## License

No license file is currently included. A license must file would be obtained before distributing or publishing the project publicly.
