# Render Environment Variables Setup Guide

## Step 1: Create PostgreSQL Database on Render

1. Go to your Render dashboard
2. Click "New +" > "PostgreSQL"
3. Configure:
   - Name: `personal-app-db`
   - Database Name: `personalapp`
   - User: `postgres`
   - Plan: Free (or paid for production)
4. Click "Create Database"

## Step 2: Get Database Connection String

1. Go to your database dashboard
2. Click "Connect" tab
3. Copy the **External Database URL**
4. It will look like: `postgresql://postgres:password@host:5432/personalapp`

## Step 3: Set Environment Variables on Render

1. Go to your web service dashboard
2. Click "Environment" tab
3. Add these environment variables:

### Required Variables:
```
FLASK_ENV = production
FLASK_SECRET_KEY = [generate secure key]
DATABASE_URL = [your database connection string]
```

### Generate Secret Key:
Use this command to generate a secure key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Or use an online generator to create a 64-character hex string.

## Step 4: Example Render Environment Variables

```
FLASK_ENV = production
FLASK_SECRET_KEY = a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2
DATABASE_URL = postgresql://postgres:abc123def456@your-db-host.compute-1.amazonaws.com:5432/personalapp
```

## Step 5: Verify Deployment

1. Push your code to GitHub
2. Render will automatically deploy
3. Check the logs for any errors
4. Test your application at the provided URL

## Important Notes:

1. **Never commit .env files** to GitHub
2. **Use Render's managed PostgreSQL** for best performance
3. **Generate a unique secret key** for each deployment
4. **Keep database credentials secure** - only use Render's provided connection string
5. **Monitor Render logs** for any connection issues

## Troubleshooting:

### Database Connection Error:
- Verify DATABASE_URL format
- Check if database is running
- Ensure database name matches

### Application Error:
- Check Flask logs in Render
- Verify all dependencies in requirements.txt
- Ensure Python version compatibility

### Permission Error:
- Check database user permissions
- Verify connection string credentials

## Quick Setup Commands:

```bash
# Generate secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Test database connection locally (optional)
python -c "import psycopg2; conn = psycopg2.connect('your-connection-string'); print('Connected!')"
```

Your application will be production-ready with these environment variables properly configured on Render!
