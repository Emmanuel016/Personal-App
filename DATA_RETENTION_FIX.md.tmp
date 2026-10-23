# Data Retention and Soft Delete Fix

## Problem Summary

**Issue**: Shared file attachments and email-invoice contents were disappearing in the production database after a while.

**Root Cause**: Aggressive `cascade="all, delete-orphan"` relationships in the database schema caused accidental mass deletions:
- When a User was deleted → ALL their projects, messages, file attachments, and invoices were deleted
- When a Project was deleted → ALL messages, file attachments, and invoices were deleted
- When a Message was deleted → ALL file attachments (including invoice content) were deleted
- No data retention policies or safeguards existed
- No recovery mechanism for accidentally deleted data

## Solution Implemented

### 1. Soft Delete Implementation

Added `deleted_at` columns to critical tables:
- `users.deleted_at` - Timestamp for soft-deleted users
- `users.is_active` - Boolean flag for active/inactive users
- `projects.deleted_at` - Timestamp for soft-deleted projects
- `messages.deleted_at` - Timestamp for soft-deleted messages
- `file_attachments.deleted_at` - Timestamp for soft-deleted attachments
- `invoices.deleted_at` - Timestamp for soft-deleted invoices

**Benefits**:
- Data is never permanently deleted (can be recovered)
- Prevents accidental data loss
- Enables data recovery and audit trails
- Complies with data retention requirements

### 2. Safe Cascade Configuration

Changed aggressive cascade deletes to safe cascades:

**Before** (DANGEROUS):
```python
projects = db.relationship("Project", backref="client", lazy=True, cascade="all, delete-orphan")
messages = db.relationship("Message", backref="client_user", lazy=True, cascade="all, delete-orphan")
invoices = db.relationship("Invoice", backref="client", lazy=True, cascade="all, delete-orphan")
```

**After** (SAFE):
```python
projects = db.relationship("Project", backref="client", lazy=True, cascade="save-update, merge")
messages = db.relationship("Message", backref="client_user", lazy=True, cascade="save-update, merge")
invoices = db.relationship("Invoice", backref="client", lazy=True, cascade="save-update, merge")
```

**Only safe cascades remain**:
- `notifications` - Safe to delete (temporary data)
- `password_reset_tokens` - Safe to delete (temporary data)
- `notification_preferences` - Safe to delete (user-specific settings)

### 3. Data Retention Policies

Added scheduled cleanup jobs with configurable retention periods:

| Data Type | Default Retention | Environment Variable | Cleanup Frequency |
|-----------|------------------|---------------------|-------------------|
| Messages | 365 days (1 year) | `MESSAGE_RETENTION_DAYS` | Daily |
| Projects | 730 days (2 years) | `PROJECT_RETENTION_DAYS` | Daily |
| Invoices | 2555 days (7 years) | `INVOICE_RETENTION_DAYS` | Daily |
| Notifications | 90 days | `NOTIFICATION_CLEANUP_DAYS` | Daily |
| Password Tokens | Based on expiry | N/A | Every 6 hours |

**Important**: All cleanups use **soft delete** (set `deleted_at`), not hard delete.

### 4. Safe Delete Operations

Updated delete functions to use soft delete:

**Project Deletion**:
```python
# Before: db.session.delete(project)  # PERMANENT DELETION
# After: project.deleted_at = datetime.now(timezone.utc)  # SOFT DELETE
```

**File Attachment Deletion**:
```python
# Before: db.session.delete(attachment)  # PERMANENT DELETION + FILE DELETION
# After: attachment.deleted_at = datetime.now(timezone.utc)  # SOFT DELETE ONLY
```

### 5. Migration Script

Created `migrate_add_soft_delete.py` to add soft delete columns to existing databases:
- Automatically adds `deleted_at` and `is_active` columns
- Safe to run multiple times (checks for existing columns)
- Integrated into `build.sh` for automatic migration on deployment

## Configuration

### Environment Variables

Add these to your `.env` file or Render dashboard:

```bash
# Data Retention Policies (in days)
# Set to 0 to disable cleanup for specific data types
MESSAGE_RETENTION_DAYS=365      # Messages retained for 1 year
PROJECT_RETENTION_DAYS=730      # Projects retained for 2 years
INVOICE_RETENTION_DAYS=2555     # Invoices retained for 7 years (legal requirement)
NOTIFICATION_CLEANUP_DAYS=90     # Notifications retained for 90 days
```

### Scheduler Configuration

The scheduler must be enabled for cleanup jobs to run:

```bash
SCHEDULER_ENABLED=true
```

## Deployment Steps

### 1. Run Migration

```bash
# Run the migration script
python migrate_add_soft_delete.py
```

Or let it run automatically during deployment (via `build.sh`).

### 2. Update Environment Variables

Add the retention policy variables to your environment:
- `.env` file for local development
- Render dashboard for production deployment

### 3. Deploy

```bash
# Deploy with Docker
docker-compose up -d --build

# Or deploy to Render
git push origin main
```

### 4. Verify

After deployment, verify:
1. Check logs for migration success: `docker-compose logs`
2. Verify scheduler is running: Check for "Scheduler started successfully"
3. Test delete operations: Should now soft delete instead of hard delete

## Data Recovery

### Recover Soft-Deleted Data

To recover soft-deleted data, you can:

**Option 1: SQL Query**
```sql
-- Recover a specific project
UPDATE projects SET deleted_at = NULL WHERE id = <project_id>;

-- Recover all projects deleted in the last 7 days
UPDATE projects SET deleted_at = NULL 
WHERE deleted_at > NOW() - INTERVAL '7 days';
```

**Option 2: Python Script**
```python
from datetime import datetime, timezone, timedelta
from models import db, Project

# Recover projects deleted in the last 7 days
cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
recovered = Project.query.filter(
    Project.deleted_at > cutoff_date
).update({"deleted_at": None})
db.session.commit()
print(f"Recovered {recovered} projects")
```

## Monitoring

### Check Soft-Deleted Data

```sql
-- Count soft-deleted items by table
SELECT 'users' as table_name, COUNT(*) as deleted_count FROM users WHERE deleted_at IS NOT NULL
UNION ALL
SELECT 'projects', COUNT(*) FROM projects WHERE deleted_at IS NOT NULL
UNION ALL
SELECT 'messages', COUNT(*) FROM messages WHERE deleted_at IS NOT NULL
UNION ALL
SELECT 'file_attachments', COUNT(*) FROM file_attachments WHERE deleted_at IS NOT NULL
UNION ALL
SELECT 'invoices', COUNT(*) FROM invoices WHERE deleted_at IS NOT NULL;
```

### Cleanup Logs

Monitor cleanup job logs:
```bash
# Docker logs
docker-compose logs -f | grep "Cleaned up"

# Render logs
# Check Render dashboard logs for cleanup messages
```

## Important Notes

### ⚠️ Critical Changes

1. **Cascade Delete Behavior Changed**: 
   - Deleting a user no longer deletes their projects, messages, or invoices
   - Deleting a project no longer deletes its messages or invoices
   - This is intentional to prevent data loss

2. **Physical File Storage**:
   - File attachments are no longer deleted from disk when soft-deleted
   - This allows recovery of uploaded files
   - Manual cleanup of orphaned files may be needed periodically

3. **Database Size**:
   - Soft-deleted data remains in the database
   - This will increase database size over time
   - Consider periodic hard delete of very old data (after legal retention period)

### Legal Compliance

- **Invoices**: 7-year retention meets UK tax law requirements
- **Projects**: 2-year retention for business records
- **Messages**: 1-year retention for communication history
- Adjust retention periods based on your local legal requirements

### Future Enhancements

Consider implementing:
1. Automated data recovery interface for admins
2. Hard delete job for data beyond legal retention period
3. Export/archive functionality for long-term storage
4. Audit logging for all delete operations

## Testing

### Test Soft Delete

```python
# Test project soft delete
project = Project.query.get(1)
project.deleted_at = datetime.now(timezone.utc)
db.session.commit()

# Verify project is soft-deleted but still in database
assert Project.query.get(1) is not None
assert Project.query.get(1).deleted_at is not None

# Verify
