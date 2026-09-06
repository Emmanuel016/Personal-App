# Deployment Guide - Personal App (Improved Version)

## Quick Start - Local Development

### 1. Setup Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/Scripts/activate  # Windows
source venv/bin/activate      # macOS/Linux

# Install dependencies (UPDATED with Flask-Limiter)
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy the example configuration
copy .env.example .env

# Edit .env with your values
# IMPORTANT: Generate a secure secret key:
python -c "import secrets; print(secrets.token_hex(32))"
# Copy the output to FLASK_SECRET_KEY in .env
```

### 3. Run Locally

```bash
# Development mode with debug
set FLASK_ENV=development
python server.py

# Production mode (like Render)
set FLASK_ENV=production  
gunicorn wsgi:app
```

Visit: http://localhost:5000

---

## Deployment to Render.com

### Step 1: Push Code to GitHub

```bash
git add .
git commit -m "Security improvements and optimizations"
git push origin main
```

### Step 2: Create Render Service

1. Go to https://render.com
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: personal-app (or your choice)
   - **Environment**: Python
   - **Build Command**: `bash build.sh`
   - **Start Command**: `bash start.sh`
   - **Plan**: Free tier is fine

### Step 3: Set Environment Variables

In Render dashboard, go to Settings → Environment and add:

```
FLASK_ENV=production
FLASK_SECRET_KEY=<your-32-char-secret>
DATABASE_URL=<PostgreSQL-connection-string>
PAYPAL_MODE=sandbox  # or live for production
PAYPAL_CLIENT_ID=<your-paypal-id>
PAYPAL_CLIENT_SECRET=<your-paypal-secret>
PORT=8000
WORKERS=2
TIMEOUT=60
```

### Step 4: Get PostgreSQL Database

**Option A: Render Postgres** (Recommended)
```
1. In Render, create new PostgreSQL instance
2. Copy connection string to DATABASE_URL
3. Click "Connect" and wait for it to be ready
```

**Option B: External Database**
```
DATABASE_URL=postgresql://user:password@hostname/dbname
```

### Step 5: Deploy

1. Push code to GitHub
2. Render auto-deploys on push
3. Check logs for errors
4. Wait ~2-3 minutes for first deploy

---

## Verification After Deployment

### Health Check
```bash
curl https://your-app.onrender.com/api/test

# Should return:
{
  "status": "success",
  "database_connected": true,
  "projects_count": 0,
  "users_count": 0
}
```

### Test Login
1. Go to https://your-app.onrender.com/login
2. Create new account (first user = admin)
3. Password must be: 8+ chars, with letters and numbers
4. Example: `AdminPass123`

### Test Rate Limiting
Try logging in wrong password 6+ times:
- Should show "Too many requests" error on 6th attempt
- Wait 1+ minute before trying again

---

## Environment Variables Reference

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `FLASK_ENV` | Yes | `production` | Never use `development` in production |
| `FLASK_SECRET_KEY` | Yes | `abc123...` | Min 32 characters, use `secrets` module |
| `DATABASE_URL` | Yes | `postgresql://...` | Required in production |
| `PAYPAL_MODE` | No | `sandbox` | Use `live` when ready |
| `PAYPAL_CLIENT_ID` | No | `ABC123...` | Get from PayPal Dashboard |
| `PAYPAL_CLIENT_SECRET` | No | `XYZ789...` | Keep secret! |
| `PORT` | No | `8000` | Default 8000 |
| `WORKERS` | No | `2` | Gunicorn workers (2 for free tier) |
| `TIMEOUT` | No | `60` | Request timeout in seconds |

---

## Troubleshooting Deployment

### "Database connection failed"
```
✓ Check DATABASE_URL is set correctly
✓ Verify PostgreSQL is running
✓ Check SSL mode settings if cloud hosted
✓ Restart service after changing DATABASE_URL
```

### "Secret key not set"
```
✓ Generate new secret: python -c "import secrets; print(secrets.token_hex(32))"
✓ Add to FLASK_SECRET_KEY environment variable
✓ Restart service
```

### "App crashes after deploy"
```
✓ Check Render logs for error messages
✓ Verify all required env vars are set
✓ Try running locally to replicate error
✓ Check database exists and is accessible
```

### "Slow requests / timeouts"
```
✓ Check /api/projects?page=1 has pagination
✓ Verify database queries are optimized
✓ Increase TIMEOUT if needed (default 60)
✓ Consider upgrading from free tier
```

---

## Production Checklist

Before going live with real users:

- [ ] Test all features (login, orders, payments, feedback)
- [ ] Set `FLASK_ENV=production` (not development)
- [ ] Use PostgreSQL (not SQLite)
- [ ] Set strong FLASK_SECRET_KEY (32+ chars)
- [ ] Enable HTTPS (Render does this automatically)
- [ ] Set up automatic daily database backups
- [ ] Configure error logging/monitoring
- [ ] Test payment flow with real PayPal account
- [ ] Verify rate limiting works (try 6 bad logins)
- [ ] Check for any sensitive data in logs
- [ ] Set up email notifications for errors
- [ ] Document any custom modifications

---

## Monitoring & Maintenance

### Daily
- Check application logs for errors
- Monitor failed payment attempts
- Check for unusual login patterns

### Weekly  
- Review user feedback for bugs
- Check database disk space usage
- Verify backups are working

### Monthly
- Update dependencies: `pip list --outdated`
- Security audit of code changes
- Review and archive old logs
- Check for deprecation warnings

---

## Rollback Procedure

If something breaks in production:

```bash
# 1. Revert code to previous commit
git revert HEAD
git push origin main

# 2. Render auto-deploys previous version
# (should take 2-3 minutes)

# 3. Verify site is back up
curl https://your-app.onrender.com/login

# 4. Investigate issue locally
# before re-deploying
```

---

## Getting Help

- **Render Docs**: https://render.com/docs
- **Flask Docs**: https://flask.palletsprojects.com
- **PostgreSQL Docs**: https://www.postgresql.org/docs/
- **Flask-Limiter**: https://flask-limiter.readthedocs.io/

---

**Estimated Deploy Time**: 2-3 minutes  
**Downtime During Deploy**: ~30 seconds  
**After Deploy**: Full testing recommended (30 mins)
