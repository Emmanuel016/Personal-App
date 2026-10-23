# Database Data Loss Fix - Summary

## Problem Identified

**Issue**: Shared file attachments and email-invoice contents were disappearing in the production database after a while.

**Root Cause**: Aggressive `cascade="all, delete-orphan"` relationships in the database schema caused accidental mass deletions when parent records were deleted.

## Changes Made

### 1. Updated models.py
- Added `deleted_at` columns to: users, projects, messages, file_attachments, invoices
- Added `is_active` column to users
- Changed cascade relationships from "all, delete-orphan" to "save-update, merge" for critical data
- Only safe cascades remain for temporary data (notifications, password tokens)

### 2. Updated server.py
- Added soft delete functions: `cleanup_old_messages()`, `cleanup_old_projects()`, `cleanup_old_invoices()`
- Changed `delete_project()` to use soft delete instead of hard delete
- Changed `delete_file()` to use soft delete instead of hard delete
- Added scheduler jobs for daily cleanup of old data
- All cleanup operations use soft delete (set deleted_at) rather than hard delete

### 3. Created migration script
- `migrate_add_soft_delete.py` - Adds soft delete columns to existing databases
- Safe to run multiple times (checks for existing columns)
- Integrated into build.sh for automatic deployment

### 4. Updated configuration files
- Added retention policy environment variables to .env.example
- Updated render.yaml with retention policy variables
- Updated build.sh to run migration automatically

### 5. Created documentation
- Comprehensive documentation in DATA_RETENTION_FIX.md
- Deployment instructions and recovery procedures
- Monitoring and troubleshooting guidance

## Data Retention Policies

| Data Type | Default Retention | Environment Variable |
|-----------|------------------|---------------------|
| Messages | 365 days (1 year) | MESSAGE_RETENTION_DAYS |
| Projects | 730 days (2 years) | PROJECT_RETENTION_DAYS |
| Invoices | 2555 days (7 years) | INVOICE_RETENTION_DAYS |
| Notifications | 90 days | NOTIFICATION_CLEANUP_DAYS |

## Key Benefits

1. **Prevents Data Loss**: Soft delete means data is never permanently deleted
2. **Recovery Capability**: Soft-deleted data can be recovered
3. **Safe Cascades**: Critical data no longer cascades deletes
4. **Legal Compliance**: 7-year invoice retention meets UK tax requirements
5. **Configurable**: Retention periods can be adjusted via environment variables
6. **Monitoring**: Cleanup jobs log all operations

## Next Steps for Production Deployment

1. **Run migration on production database**:
   ```bash
   python migrate_add_soft_delete.py
   ```

2. **Add environment variables to Render dashboard**:
   - MESSAGE_RETENTION_DAYS=365
   - PROJECT_RETENTION_DAYS=730
   - INVOICE_RETENTION_DAYS=2555
   - NOTIFICATION_CLEANUP_DAYS=90

3. **Deploy to production**:
   ```bash
   git add .
   git commit -m "Fix: Implement soft delete and data retention policies"
   git push origin main
   ```

4. **Verify deployment**:
   - Check Render logs for migration success
   - Verify scheduler is running
   - Test delete operations (should soft delete)

## Files Modified

- `models.py` - Added soft delete columns and safe cascades
- `server.py` - Added cleanup functions and soft delete operations
- `migrate_add_soft_delete.py` - New migration script
- `build.sh` - Added migration check
- `render.yaml` - Added retention policy variables
- `.env.example` - Added retention policy variables
- `models.py.backup` - Backup of original models.py
- `server.py.backup` - Backup of original server.py

## Rollback Plan

If issues occur:
1. Restore models.py.backup and server.py.backup
2. Remove retention policy environment variables
3. Redeploy

**Warning**: Rolling back will re-enable aggressive cascade deletes and potential data loss.

## Testing

Test locally before production deployment:
```bash
# Run migration
python migrate_add_soft_delete.py

# Start server
python server.py

# Test delete operations (should soft delete)
# Verify data is not permanently deleted
```

## Support

For issues:
1. Check logs: `logs/app.log`
2. Verify migration: Check deleted_at columns exist
3. Verify scheduler: Check for "Scheduler started successfully"
4. Review DATA_RETENTION_FIX.md for detailed troubleshooting
