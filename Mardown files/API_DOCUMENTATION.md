# EMMA.STUDIO API Documentation

## Overview

This API documentation covers all endpoints for the EMMA.STUDIO Client Management System. The API provides functionality for user authentication, client management, project tracking, invoicing, file management, and real-time notifications.

**Base URL**: `http://localhost:5000` (development) or your production domain

**Content Type**: `application/json`

**Authentication**: Session-based authentication required for most endpoints

---

## Authentication & Authorization

### Authentication Method

The API uses session-based authentication. Users must log in via the `/login` endpoint to establish a session. The session cookie is automatically included in subsequent requests.

### User Roles

- **Admin**: Full access to all endpoints including client management, project creation, and invoice generation
- **Client**: Limited access to their own data, messaging, and notifications

### Rate Limiting

- **General API**: 1,000,000 requests per hour
- **Admin endpoints**: 200,000 requests per hour  
- **Login/Register**: 5,000 requests per minute

---

## Response Format

### Success Response

```json
{
  "status": "success",
  "data": { ... }
}
```

### Error Response

```json
{
  "error": "Error message description"
}
```

### HTTP Status Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error

---

## Authentication Endpoints

### POST /login

Authenticate a user and establish a session.

**Rate Limit**: 5,000 requests per minute

**Request Body**:
```json
{
  "username": "string",
  "password": "string"
}
```

**Response**:
- On success: Redirects to dashboard
- On failure: Returns error message

### POST /register

Register a new user account.

**Rate Limit**: 5,000 requests per minute

**Request Body**:
```json
{
  "username": "string",
  "password": "string",
  "email": "string",
  "company": "string (optional)",
  "phone": "string (optional)",
  "notes": "string (optional)"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Registration successful"
}
```

### POST /forgot-password

Request a password reset link.

**Rate Limit**: 5,000 requests per minute

**Request Body**:
```json
{
  "email": "string"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Password reset email sent"
}
```

### POST /reset-password/<token>

Reset password using a valid token.

**Request Body**:
```json
{
  "password": "string",
  "confirm_password": "string"
}
```

**Response**:
- On success: Redirects to login page
- On failure: Returns error message

### GET /logout

End the current session and log out the user.

**Response**: Redirects to login page

---

## Dashboard Endpoints

### GET /

Render the admin dashboard page.

**Authentication**: Required (Admin)

### GET /client/dashboard

Render the client portal dashboard.

**Authentication**: Required (Client)

### GET /api/dashboard

Get dashboard statistics and data.

**Authentication**: Required

**Response**:
```json
{
  "total_revenue": 10000.00,
  "total_paid": 5000.00,
  "status_counts": {
    "Active": 5,
    "Completed": 3,
    "Pending": 2
  }
}
```

---

## Client Management Endpoints

### GET /clients

Render the clients management page.

**Authentication**: Required (Admin)

### GET /api/clients

Get list of all clients.

**Authentication**: Required (Admin)

**Query Parameters**:
- `page` (optional): Page number for pagination
- `per_page` (optional): Items per page (max 100)

**Response**:
```json
{
  "data": [
    {
      "id": 1,
      "username": "client_name",
      "email": "client@example.com",
      "company": "Company Name",
      "phone": "+1234567890",
      "role": "client",
      "date_added": "2024-01-01"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 100,
    "pages": 2
  }
}
```

### POST /api/clients/add

Add a new client.

**Authentication**: Required (Admin)

**Request Body**:
```json
{
  "username": "string",
  "email": "string",
  "company": "string (optional)",
  "phone": "string (optional)",
  "notes": "string (optional)",
  "role": "client"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Client added successfully"
}
```

### GET /api/profile

Get current user profile information.

**Authentication**: Required

**Response**:
```json
{
  "id": 1,
  "username": "username",
  "email": "user@example.com",
  "company": "Company Name",
  "role": "admin"
}
```

---

## Project Management Endpoints

### GET /projects

Render the projects management page.

**Authentication**: Required (Admin)

### GET /api/projects

Get list of projects.

**Authentication**: Required

**Query Parameters**:
- `page` (optional): Page number for pagination
- `per_page` (optional): Items per page (max 100)

**Response**:
```json
{
  "data": [
    {
      "id": 1,
      "client_user_id": 2,
      "client_name": "Client Name",
      "client_details": {
        "username": "client_name",
        "email": "client@example.com",
        "company": "Company Name"
      },
      "title": "Project Title",
      "desc": "Project description",
      "status": "Active",
      "price": 1000.00,
      "amount_paid": 500.00,
      "deadline": "2024-12-31",
      "attached_files": [
        {
          "id": 1,
          "original_filename": "file.pdf",
          "file_size": 1024,
          "download_url": "/api/files/1/download"
        }
      ]
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 50,
    "pages": 1
  }
}
```

### POST /api/projects

Create a new project.

**Authentication**: Required

**Request Body**:
```json
{
  "client_user_id": 2,
  "title": "Project Title",
  "desc": "Project description",
  "price": 1000.00,
  "status": "Active",
  "deadline": "2024-12-31"
}
```

**Response**:
```json
{
  "status": "success",
  "project": {
    "id": 1,
    "title": "Project Title"
  }
}
```

### PATCH /api/projects/<int:project_id>

Update an existing project.

**Authentication**: Required (Admin)

**Request Body**:
```json
{
  "title": "Updated Title",
  "desc": "Updated description",
  "status": "Completed",
  "price": 1500.00,
  "deadline": "2024-12-31"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Project updated successfully"
}
```

### POST /api/projects/<int:project_id>/payment

Add a payment to a project.

**Authentication**: Required (Admin)

**Request Body**:
```json
{
  "amount": 500.00
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Payment added successfully"
}
```

### DELETE /api/projects/<int:project_id>

Delete a project.

**Authentication**: Required (Admin)

**Response**:
```json
{
  "status": "success",
  "message": "Project deleted successfully"
}
```

---

## Messaging Endpoints

### GET /api/messages/<int:target_id>

Get messages between current user and target user.

**Authentication**: Required

**Response**:
```json
{
  "messages": [
    {
      "id": 1,
      "sender": "admin",
      "content": "Message content",
      "timestamp": "2024-01-01T12:00:00",
      "attachments": [
        {
          "id": 1,
          "original_filename": "file.pdf",
          "file_size": 1024
        }
      ]
    }
  ]
}
```

### POST /api/messages/<int:target_id>

Send a message to target user.

**Authentication**: Required

**Request Body**:
```json
{
  "content": "Message content",
  "sender": "admin",
  "timestamp": "2024-01-01T12:00:00"
}
```

**Response**:
```json
{
  "status": "success",
  "message": {
    "id": 1,
    "content": "Message content"
  }
}
```

### POST /api/messages/<int:message_id>/upload

Upload a file attachment to a message.

**Authentication**: Required

**Request Body**: `multipart/form-data`
- `file`: The file to upload

**Response**:
```json
{
  "status": "success",
  "message": "File uploaded successfully",
  "file": {
    "id": 1,
    "original_filename": "file.pdf",
    "file_size": 1024
  }
}
```

### GET /api/messages/<int:target_id>/files

Get all files shared with target user.

**Authentication**: Required

**Response**:
```json
{
  "files": [
    {
      "id": 1,
      "original_filename": "file.pdf",
      "file_size": 1024,
      "upload_date": "2024-01-01T12:00:00"
    }
  ]
}
```

---

## File Management Endpoints

### GET /api/files/<int:file_id>/download

Download a file by ID.

**Authentication**: Required

**Response**: File download

### DELETE /api/files/<int:file_id>

Delete a file by ID.

**Authentication**: Required

**Response**:
```json
{
  "status": "success",
  "message": "File deleted successfully"
}
```

---

## Invoice Endpoints

### GET /invoices

Render the invoices management page.

**Authentication**: Required (Admin)

### GET /api/invoices

Get list of invoices.

**Authentication**: Required

**Query Parameters**:
- `page` (optional): Page number for pagination
- `per_page` (optional): Items per page (max 100)

**Response**:
```json
{
  "data": [
    {
      "id": 1,
      "invoice_number": "INV-20240101-ABC123",
      "project_id": 1,
      "client_id": 2,
      "amount": 1000.00,
      "status": "pending",
      "due_date": "2024-01-31",
      "created_at": "2024-01-01T12:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 20,
    "pages": 1
  }
}
```

### POST /api/invoices/generate

Generate a new invoice for a project.

**Authentication**: Required (Admin)

**Request Body**:
```json
{
  "project_id": 1,
  "invoice_type": "completion"
}
```

**Response**:
```json
{
  "status": "success",
  "invoice": {
    "id": 1,
    "invoice_number": "INV-20240101-ABC123",
    "amount": 1000.00
  }
}
```

### GET /api/invoices/<int:invoice_id>/pay

Get payment link for an invoice.

**Authentication**: Required

**Response**:
```json
{
  "payment_url": "https://paypal.com/checkout/..."
}
```

### POST /api/invoices/<int:invoice_id>/capture

Capture payment for an invoice.

**Authentication**: Required

**Request Body**:
```json
{
  "payment_id": "PAYPAL_PAYMENT_ID",
  "payer_id": "PAYPAL_PAYER_ID"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Payment captured successfully"
}
```

### GET /api/invoices/<int:invoice_id>/pdf

Generate and download invoice PDF.

**Authentication**: Required

**Response**: PDF file download

### POST /api/invoices/<int:invoice_id>/resend

Resend invoice email to client.

**Authentication**: Required (Admin)

**Response**:
```json
{
  "status": "success",
  "message": "Invoice email resent successfully"
}
```

### POST /api/invoices/<int:invoice_id>/mark-paid

Manually mark an invoice as paid.

**Authentication**: Required (Admin)

**Response**:
```json
{
  "status": "success",
  "message": "Invoice marked as paid"
}
```

---

## Payment Endpoints

### POST /api/payment/submit

Submit a payment for an invoice.

**Authentication**: Required

**Request Body**:
```json
{
  "invoice_id": 1,
  "amount": 1000.00
}
```

**Response**:
```json
{
  "status": "success",
  "payment_id": "PAYMENT_ID"
}
```

### POST /api/paypal/create-payment

Create a PayPal payment.

**Authentication**: Required

**Request Body**:
```json
{
  "amount": 1000.00,
  "currency": "USD",
  "description": "Payment description"
}
```

**Response**:
```json
{
  "payment_id": "PAYPAL_PAYMENT_ID",
  "approval_url": "https://paypal.com/checkout/..."
}
```

### POST /api/paypal/execute-payment

Execute a PayPal payment.

**Authentication**: Required

**Request Body**:
```json
{
  "payment_id": "PAYPAL_PAYMENT_ID",
  "payer_id": "PAYPAL_PAYER_ID"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Payment executed successfully"
}
```

### GET /api/paypal/cancel-payment

Cancel a PayPal payment.

**Authentication**: Not required

**Response**: Redirects to invoices page

---

## Notification Endpoints

### GET /notifications

Render the notifications page.

**Authentication**: Required (Admin)

### GET /client/notifications

Render the client notifications page.

**Authentication**: Required (Client)

### GET /api/notifications

Get notifications for current user.

**Authentication**: Required

**Query Parameters**:
- `page` (optional): Page number for pagination
- `per_page` (optional): Items per page (max 100)

**Response**:
```json
{
  "notifications": [
    {
      "id": 1,
      "type": "message",
      "title": "New Message",
      "message": "You have a new message",
      "read": false,
      "created_at": "2024-01-01T12:00:00",
      "data": {
        "message_id": 1
      }
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 50,
    "pages": 3
  }
}
```

### GET /api/notifications/stats

Get notification statistics.

**Authentication**: Required

**Response**:
```json
{
  "total": 50,
  "unread": 10,
  "read": 40
}
```

### POST /api/notifications/<int:notification_id>/read

Mark a notification as read.

**Authentication**: Required

**Response**:
```json
{
  "status": "success",
  "message": "Notification marked as read"
}
```

### POST /api/notifications/mark-all-read

Mark all notifications as read.

**Authentication**: Required

**Response**:
```json
{
  "status": "success",
  "message": "All notifications marked as read"
}
```

### DELETE /api/notifications/<int:notification_id>

Delete a notification.

**Authentication**: Required

**Response**:
```json
{
  "status": "success",
  "message": "Notification deleted"
}
```

### DELETE /api/notifications/delete-read

Delete all read notifications.

**Authentication**: Required

**Response**:
```json
{
  "status": "success",
  "message": "Read notifications deleted"
}
```

---

## Admin Notification Endpoints

### GET /api/admin/notifications

Get admin notifications.

**Authentication**: Required (Admin)

**Response**: Same format as `/api/notifications`

### GET /api/admin/notifications/stats

Get admin notification statistics.

**Authentication**: Required (Admin)

**Response**: Same format as `/api/notifications/stats`

### POST /api/admin/notifications/<int:notification_id>/read

Mark admin notification as read.

**Authentication**: Required (Admin)

**Response**: Same format as `/api/notifications/<id>/read`

### POST /api/admin/notifications/mark-all-read

Mark all admin notifications as read.

**Authentication**: Required (Admin)

**Response**: Same format as `/api/notifications/mark-all-read`

### DELETE /api/admin/notifications/<int:notification_id>

Delete admin notification.

**Authentication**: Required (Admin)

**Response**: Same format as `/api/notifications/<id>`

### DELETE /api/admin/notifications/delete-read

Delete all read admin notifications.

**Authentication**: Required (Admin)

**Response**: Same format as `/api/notifications/delete-read`

---

## Client Notification Endpoints

### GET /api/client/notifications

Get client notifications.

**Authentication**: Required

**Response**: Same format as `/api/notifications`

### GET /api/client/notifications/stats

Get client notification statistics.

**Authentication**: Required

**Response**: Same format as `/api/notifications/stats`

### POST /api/client/notifications/<int:notification_id>/read

Mark client notification as read.

**Authentication**: Required

**Response**: Same format as `/api/notifications/<id>/read`

### POST /api/client/notifications/mark-all-read

Mark all client notifications as read.

**Authentication**: Required

**Response**: Same format as `/api/notifications/mark-all-read`

### DELETE /api/client/notifications/<int:notification_id>

Delete client notification.

**Authentication**: Required

**Response**: Same format as `/api/notifications/<id>`

### DELETE /api/client/notifications/delete-read

Delete all read client notifications.

**Authentication**: Required

**Response**: Same format as `/api/notifications/delete-read`

---

## Service Endpoints

### GET /services

Render the services page.

**Authentication**: Not required

### GET /api/services

Get available services.

**Authentication**: Not required

**Response**:
```json
{
  "services": [
    {
      "id": 1,
      "name": "Web Development",
      "description": "Custom web development services",
      "price": 1000.00
    }
  ]
}
```

---

## Feedback Endpoints

### GET /client_feedback

Render the client feedback page.

**Authentication**: Required (Client)

### GET /api/feedback

Get feedback submissions.

**Authentication**: Not required

**Response**:
```json
{
  "feedback": [
    {
      "id": 1,
      "client_id": 2,
      "rating": 5,
      "comment": "Great service!",
      "created_at": "2024-01-01T12:00:00"
    }
  ]
}
```

### POST /api/feedback

Submit feedback.

**Authentication**: Not required

**Request Body**:
```json
{
  "rating": 5,
  "comment": "Great service!"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Feedback submitted successfully"
}
```

---

## Order Endpoints

### GET /client/order

Render the client order page.

**Authentication**: Required (Client)

### POST /api/orders

Place a new order.

**Authentication**: Required

**Request Body**:
```json
{
  "service_id": 1,
  "description": "Order description",
  "budget": 1000.00
}
```

**Response**:
```json
{
  "status": "success",
  "order_id": 1
}
```

---

## WebSocket Events

### Connection

The application uses Socket.IO with long-polling transport for real-time notifications.

**Client Connection**:
```javascript
const socket = io({
  transports: ['polling'],
  upgrade: false
});
```

### Events

#### connect

Emitted when client connects to server.

#### disconnect

Emitted when client disconnects from server.

#### new_notification

Server emits this event when a new notification is created.

**Payload**:
```json
{
  "id": 1,
  "type": "message",
  "title": "New Message",
  "message": "You have a new message",
  "read": false,
  "created_at": "2024-01-01T12:00:00",
  "data": {}
}
```

#### mark_notification_read

Client emits this to mark a notification as read.

**Payload**:
```json
{
  "notification_id": 1
}
```

#### get_notifications

Client emits this to request notifications.

**Payload**:
```json
{
  "page": 1,
  "per_page": 20
}
```

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "error": "Error message description"
}
```

Common error messages:
- "Unauthorized" - Authentication required or invalid
- "Forbidden" - Insufficient permissions
- "Invalid input" - Request validation failed
- "Resource not found" - Requested resource doesn't exist
- "Server error" - Internal server error

---

## File Upload Constraints

- **Maximum file size**: 100 MB
- **Allowed extensions**: txt, pdf, png, jpg, jpeg, gif, mp4, xml, avi, mov, mkv, md, webp, cpp, doc, html, docx, xls, xlsx, json, zip, ppt, pptx, webm, mp3, wav, csv, css, py
- **Filename sanitization**: Automatic sanitization for security
- **Storage**: Local filesystem (development) or persistent disk mount (production)

---

## Security Features

- **CSRF Protection**: Enabled for all forms
- **Session Security**: HTTP-only, secure cookies in production
- **Input Sanitization**: All user inputs are sanitized
- **Password Hashing**: bcrypt with 12 rounds
- **Rate Limiting**: Configured per endpoint
- **File Validation**: Extension and size validation
- **Path Traversal Protection**: Safe path resolution for file operations

---

## Environment Variables

Required environment variables for production:

```env
DATABASE_URL=postgresql://user:password@host/database
FLASK_SECRET_KEY=your-secret-key
PAYPAL_MODE=sandbox
PAYPAL_CLIENT_ID=your-paypal-client-id
PAYPAL_CLIENT_SECRET=your-paypal-client-secret
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@emmastudio.com
```

---

## Scheduled Tasks

The application automatically runs these scheduled tasks:

1. **Invoice Reminders** - Every hour
2. **Deadline Reminders** - Every 6 hours  
3. **Notification Cleanup** - Every 24 hours
4. **Reset Token Cleanup** - Every 6 hours

---

## Support

For issues or questions about the API, contact the development team or refer to the project README.md file.
