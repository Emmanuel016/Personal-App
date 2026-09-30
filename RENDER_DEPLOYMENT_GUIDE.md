# Render Deployment Guide - Step by Step

## Overview
This guide will walk you through deploying your Personal App to Render using Supabase database and Brevo email services.

## Prerequisites
- Render account (free tier available)
- GitHub account
- Supabase project with database
- Brevo account with API key
- Your code ready in a GitHub repository

## Step 1: Set Up GitHub Repository

### 1.1 Initialize Git (if not already done)
```bash
cd "C:\Users\user\Documents\Personal App (SUPEBASE DEPLOYMENT)"
git init
```

### 1.2 Create .gitignore (verify it exists)
```bash
# Check .gitignore includes:
.env
.env.*
.env.superbase
.env.render
.flask_secret_key
```

### 1.3 Commit Your Code
```bash
git add .
git commit -m "Initial commit - Personal App with Supabase and Brevo"
```

### 1.4 Create GitHub Repository
1. Go to https://github.com/new
2. Repository name: `personal-app` (or your preferred name)
3. Make it **Private** (recommended for security)
4. Don't initialize with README, .gitignore, or license
5. Click "Create repository"

### 1.5 Push to GitHub
```bash
# Add remote (replace with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/personal-app.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## Step 2: Set Up Render Account

### 2.1 Create Render Account
1. Go to https://render.com/
2. Click "Sign Up"
3. Sign up with GitHub (recommended)
4. Verify your email

### 2.2 Authorize Render
1. Render will ask for GitHub access
2. Grant access to your repositories
3. Select your `personal-app` repository

## Step 3: Prepare Your Code for Render

### 3.1 Verify render.yaml
Your `render.yaml` should be ready. Let me verify the key parts:

```yaml
services:
  - type: web
    name: personal-app
    env: python
    plan: free
    pythonVersion: 3.12.0
    buildCommand: bash build.sh
    startCommand: bash start.sh
    envVars:
      - key: FLASK_ENV
        value: production
      - key: DATABASE_URL
        fromDatabase:
          name: personal-app-db
          property: connectionString
      # ... other variables
```

### 3.2 Create Supabase Database in Render (Optional)
**Option A: Use External Supabase (Recommended)**
- Keep your existing Supabase database
- Configure DATABASE_URL manually in Render

**Option B: Create Render PostgreSQL**
- Let Render create a PostgreSQL database
- Skip this for now - use your existing Supabase

### 3.3 Update render.yaml for External Supabase
Modify your `render.yaml` to use external Supabase:

```yaml
services:
  - type: web
    name: personal-app
    env: python
    plan: free
    pythonVersion: 3.12.0
    buildCommand: bash build.sh
    startCommand: bash start.sh
    envVars:
      - key: FLASK_ENV
        value: production
      - key: FLASK_DEBUG
        value: "False"
      - key: FLASK_AUTO_RELOAD
        value: "false"
      - key: HTTPS_ONLY
        value: "true"
      - key: PORT
        value: "5000"
      # IMPORTANT: Remove the database reference
      # We'll add DATABASE_URL manually in Render dashboard
      - key: DATABASE_URL
        sync: false  # Will be set manually
      - key: ALLOWED_ORIGINS
        value: "https://your-app-name.onrender.com"
      - key: APP_BASE_URL
        value: "https://your-app-name.onrender.com/"
      # Email configuration
      - key: MAIL_API_KEY
        sync: false
      - key: MAIL_DEFAULT_SENDER
        sync: false
      - key: MAIL_SERVER
        value: smtp-relay.brevo.com
      - key: MAIL_PORT
        value: "587"
      - key: MAIL_USE_TLS
        value: "True"
      # Add other variables from your .env.superbase
      - key: COMPANY_NAME
        value: EmmaStudio
      - key: COMPANY_EMAIL
        value: support@emmastudio.com
      # ... add all other variables from your .env.superbase

    healthCheckPath: /api/test
    numInstances: 1

# Remove the databases section since we're using external Supabase
```

### 3.4 Commit Updated render.yaml
```bash
git add render.yaml
git commit -m "Update render.yaml for external Supabase"
git push
```

## Step 4: Deploy to Render

### 4.1 Create New Web Service
1. Go to Render Dashboard: https://dashboard.render.com/
2. Click "New +"
3. Select "Web Service"

### 4.2 Connect Repository
1. Select your GitHub repository: `personal-app`
2. Click "Connect"

### 4.3 Configure Build Settings
1. **Name**: `personal-app` (or your preferred name)
2. **Region**: Choose nearest region (e.g., Oregon, Frankfurt)
3. **Branch**: `main`
4. **Runtime**: `Python 3`
5. **Build Command**: `bash build.sh`
6. **Start Command**: `bash start.sh`

### 4.4 Configure Environment Variables
**IMPORTANT**: Don't use your exposed credentials! Rotate them first.

#### 4.4.1 Rotate Credentials First
```bash
# Before deployment, rotate these:
# 1. Supabase database password
# 2. Brevo API key
```

#### 4.4.2 Add Environment Variables in Render
In the "Environment" section of Render dashboard, add these:

**Required Variables:**
```
FLASK_ENV = production
FLASK_DEBUG = False
FLASK_AUTO_RELOAD = false
HTTPS_ONLY = true
PORT = 5000

# Database (Supabase)
DATABASE_URL = postgresql://postgres:NEW_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres

# Email (Brevo)
MAIL_API_KEY = NEW_BREVO_API_KEY
MAIL_DEFAULT_SENDER = emma.studio016@gmail.com
MAIL_SERVER = smtp-relay.brevo.com
MAIL_PORT = 587
MAIL_USE_TLS = True

# Application URLs (Render will provide these after deployment)
ALLOWED_ORIGINS = https://personal-app-xxxx.onrender.com
APP_BASE_URL = https://personal-app-xxxx.onrender.com/
```

**Optional Variables (from your .env.superbase):**
```
SCHEDULER_ENABLED = true
WORKERS = 1
THREADS = 50
TIMEOUT = 120
MAX_REQUESTS = 1000
MAX_REQUESTS_JITTER = 100
NOTIFICATION_CLEANUP_DAYS = 90
DEADLINE_REMINDER_SCHEDULE = 7,3,1,-1

# Company Info
COMPANY_NAME = EmmaStudio
COMPANY_ADDRESS = Professional Freelancing Services
COMPANY_CITY = Dudley
COMPANY_COUNTRY = England
COMPANY_PHONE = +447522617638
COMPANY_EMAIL = support@emmastudio.com

# Payment Settings
PAYMENT_METHODS = PayPal, Bank Transfer
LATE_FEE = 5% per month on overdue amount
EARLY_DISCOUNT = 2% discount if paid within 10 days
INVOICE_PREFIX = INV-
INVOICE_DUE_DAYS = 30
INVOICE_REMINDER_SCHEDULE = 7,1,-1,-7

# PayPal (if using)
PAYPAL_MODE = sandbox
PAYPAL_CLIENT_ID = your_client_id
PAYPAL_CLIENT_SECRET = your_client_secret
```

### 4.5 Choose Plan
1. **Plan**: Select "Free" (good for testing)
2. Free plan includes:
   - 512 MB RAM
   - 0.1 CPU
   - Sleeps after 15 minutes of inactivity
   - Takes ~30 seconds to wake up

### 4.6 Deploy
1. Click "Create Web Service"
2. Render will start building and deploying
3. Watch the logs in the "Logs" tab
4. Wait for deployment to complete (5-10 minutes)

## Step 5: Post-Deployment Configuration

### 5.1 Get Your Render URL
After deployment, Render will provide a URL like:
```
https://personal-app-abc123.onrender.com
```

### 5.2 Update ALLOWED_ORIGINS and APP_BASE_URL
1. Go to your Render service dashboard
2. Click "Environment"
3. Update these variables:
   ```
   ALLOWED_ORIGINS = https://personal-app-abc123.onrender.com
   APP_BASE_URL = https://personal-app-abc123.onrender.com/
   ```
4. Click "Save Changes"
5. Render will automatically redeploy

### 5.3 Verify Deployment
1. Go to your Render URL
2. Test the application:
   - Navigate to home page
   - Try to register a user
   - Test login functionality
3. Check API endpoint:
   ```
   https://personal-app-abc123.onrender.com/api/test
   ```

## Step 6: Test Database Connection

### 6.1 Check Supabase Dashboard
1. Go to your Supabase project
2. Navigate to "Table Editor"
3. Verify tables were created:
   - users
   - projects
   - messages
   - invoices
   - notifications
   - etc.

### 6.2 Test Database Operations
1. Register a new user in your app
2. Check if user appears in Supabase "users" table
3. Create a project
4. Check if project appears in Supabase "projects" table

## Step 7: Test Email Configuration

### 7.1 Send Test Email
1. Log in to your application as admin
2. Navigate to the test email endpoint (if available)
3. Send a test email to your email address

### 7.2 Check Brevo Dashboard
1. Go to Brevo Dashboard
2. Navigate to "Transactional" > "Emails"
3. Verify email was sent and delivered
4. Check for any delivery errors

### 7.3 Test Email Links
1. Trigger an email with links (e.g., password reset)
2. Click the link in the email
3. Verify it works correctly

## Step 8: Monitor and Troubleshoot

### 8.1 View Render Logs
1. Go to Render service dashboard
2. Click "Logs" tab
3. Check for errors or warnings
4. Common issues to look for:
   - Database connection errors
   - Email sending errors
   - Import errors

### 8.2 Common Issues and Solutions

#### Issue: Database Connection Failed
**Solution:**
1. Verify DATABASE_URL is correct
2. Check Supabase project is active
3. Ensure SSL is enabled (should be automatic)

#### Issue: Email Not Sending
**Solution:**
1. Verify MAIL_API_KEY is correct
2. Check Brevo account has credits
3. Review Brevo dashboard for errors
4. Try adding SMTP fallback credentials

#### Issue: Application Won't Start
**Solution:**
1. Check build logs for errors
2. Verify all dependencies are in requirements.txt
3. Check Python version matches (3.12)
4. Review start command in render.yaml

#### Issue: Scheduler Not Running
**Solution:**
1. Ensure SCHEDULER_ENABLED=true
2. Check logs for scheduler errors
3. Free plan may sleep, affecting scheduler

## Step 9: Production Considerations

### 9.1 Upgrade from Free Plan (Optional)
Free plan limitations:
- Sleeps after 15 minutes inactivity
- 512 MB RAM
- Slow wake-up time

Consider upgrading if:
- You need always-on service
- You need more resources
- You have paying customers

### 9.2 Add Custom Domain (Optional)
1. Buy a domain (e.g., from Namecheap, GoDaddy)
2. Go to Render service dashboard
3. Click "Domains"
4. Add your custom domain
5. Update DNS settings
6. Render provides automatic SSL

### 9.3 Set Up Monitoring
1. Configure Render logs retention
2. Set up error tracking (e.g., Sentry)
3. Monitor Supabase database performance
4. Track Brevo email statistics

## Step 10: Security Checklist

### 10.1 Verify Security
- [ ] Rotated Supabase database password
- [ ] Rotated Brevo API key
- [ ] No .env files committed to Git
- [ ] GitHub repository is private
- [ ] Environment variables set in Render dashboard
- [ ] HTTPS enabled (automatic on Render)
- [ ] Rate limiting configured (already in code)

### 10.2 Backup Strategy
- [ ] Supabase automatic backups enabled
- [ ] Regular database exports
- [ ] Backups of environment variables (secure, offline)
- [ ] Document recovery procedures

## Quick Reference

### Render Dashboard
- Dashboard: https://dashboard.render.com/
- Your service: https://dashboard.render.com/services/your-service-id

### Useful Commands
```bash
# View logs (in Render dashboard, not terminal)
# Go to Logs tab in Render

# Redeploy (trigger via Git)
git add .
git commit -m "Update deployment"
git push

# Environment variables
# Set in Render dashboard, not in code
```

### URLs
- Your app: https://personal-app-xxxx.onrender.com
- Supabase: https://supabase.com/dashboard
- Brevo: https://brevo.com/

## Next Steps

1. **Rotate credentials** before deployment
2. **Follow this guide** step by step
3. **Test thoroughly** after deployment
4. **Monitor logs** for any issues
5. **Ask for help** if you encounter problems

## Troubleshooting Help

If you encounter issues:
1. Check Render logs first
2. Verify environment variables
3. Test database connection
4. Review this guide
5. Ask for specific help with error messages

Good luck with your deployment! 🚀
