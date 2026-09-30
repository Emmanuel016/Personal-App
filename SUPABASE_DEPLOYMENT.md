# Supabase Deployment Guide

This guide will help you deploy your Personal App to Supabase using Brevo SMTP for email services.

## Prerequisites

- Supabase account and project
- Brevo account for email services
- PayPal developer account (optional, for payments)
- Docker installed on your local machine or deployment server

## Step 1: Supabase Database Setup

1. **Create a Supabase Project**
   - Go to [supabase.com](https://supabase.com)
   - Create a new project
   - Wait for the database to be provisioned

2. **Get Database Connection String**
   - Go to your Supabase project dashboard
   - Navigate to Settings > Database
   - Copy the "Connection String" (URI format)
   - Format: `postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`

3. **Test Database Connection**

   ```bash
   psql "postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"
   ```

## Step 2: Brevo Email Configuration

1. **Create Brevo Account**
   - Go to [brevo.com](https://brevo.com)
   - Sign up for a free account

2. **Get API Key (Recommended)**
   - Navigate to SMTP & API > API Keys
   - Create a new API key
   - Copy the API key

3. **Alternative: SMTP Credentials**
   - Navigate to SMTP & API > SMTP
   - Copy your SMTP credentials
   - Default server: `smtp-relay.brevo.com`
   - Port: `587`
   - Use TLS: `True`

## Step 3: Environment Configuration

Create a `.env` file in your project root with the following variables:

```bash
# Supabase Database
DATABASE_URL=postgresql://postgres:your_password@db.your_project_ref.supabase.co:5432/postgres

# Brevo Email (API - Recommended)
MAIL_API_KEY=your_brevo_api_key_here
MAIL_DEFAULT_SENDER=your_email@example.com

# Brevo Email (SMTP - Fallback)
MAIL_USERNAME=your_brevo_smtp_username
MAIL_PASSWORD=your_brevo_smtp_password
MAIL_SERVER=smtp-relay.brevo.com
MAIL_PORT=587
MAIL_USE_TLS=True

# PayPal (Optional)
PAYPAL_MODE=sandbox
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_client_secret

# Company Info
COMPANY_NAME=EmmaStudio
COMPANY_EMAIL=contact@emmastudio.com

# Application
FLASK_ENV=production
FLASK_DEBUG=False
HTTPS_ONLY=true
PORT=5000
ALLOWED_ORIGINS=https://your-domain.com
APP_BASE_URL=https://your-domain.com/

# Scheduler
SCHEDULER_ENABLED=true
```

## Step 4: Docker Deployment

### Option A: Docker Compose (Recommended)

1. **Build and run with Docker Compose**

   ```bash
   docker-compose up -d --build
   ```

2. **View logs**

   ```bash
   docker-compose logs -f
   ```

3. **Stop the application**

   ```bash
   docker-compose down
   ```

### Option B: Docker Standalone

1. **Build the image**

   ```bash
   docker build -t personal-app .
   ```

2. **Run the container**

   ```bash
   docker run -d \
     --name personal-app \
     -p 5000:5000 \
     --env-file .env \
     -v $(pwd)/uploads:/app/uploads \
     -v $(pwd)/logs:/app/logs \
     -v $(pwd)/pdf_cache:/app/pdf_cache \
     personal-app
   ```

## Step 5: Database Initialization

The application will automatically create all required tables on first startup. You can verify this by:

1. **Check Supabase Dashboard**
   - Go to your Supabase project
   - Navigate to Table Editor
   - You should see tables: users, projects, messages, invoices, etc.

2. **Test API Endpoint**

   ```bash
   curl http://localhost:5000/api/test
   ```

## Step 6: Verify Email Configuration

1. **Test Email Configuration**
   - Log in to your application as admin
   - Navigate to the test email endpoint
   - Send a test email to verify Brevo configuration

2. **Check Email Logs**
   - View application logs: `docker-compose logs -f`
   - Look for "Brevo API email sent successfully" messages

## Step 7: Production Deployment

### Deploy to a VPS (DigitalOcean, Linode, etc.)

1. **Install Docker on your VPS**

   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   ```

2. **Upload your files**

   ```bash
   scp -r . user@your-vps-ip:/app/
   ```

3. **Run Docker Compose**

   ```bash
   ssh user@your-vps-ip
   cd /app
   docker-compose up -d --build
   ```

### Deploy with Nginx Reverse Proxy

1. **Install Nginx**

   ```bash
   sudo apt update
   sudo apt install nginx
   ```

2. **Configure Nginx**

   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

3. **Enable SSL with Let's Encrypt**

   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

## Troubleshooting

### Database Connection Issues

- Verify your DATABASE_URL is correct
- Check Supabase project status
- Ensure your IP is whitelisted in Supabase settings

### Email Not Sending

- Verify MAIL_API_KEY is correct
- Check Brevo account status and credits
- Review application logs for error messages
- Test with SMTP fallback if API fails

### File Upload Issues

- Ensure upload directories have proper permissions
- Check disk space on your server
- Verify volume mounts in Docker configuration

## Monitoring

### Application Logs

```bash
docker-compose logs -f web
```

### Database Queries

- Use Supabase Dashboard to monitor database performance
- Check query logs in Supabase settings

### Email Statistics

- Monitor email delivery in Brevo dashboard
- Track bounce rates and spam complaints

## Security Best Practices

1. **Never commit .env files to version control**
2. **Use strong, unique passwords for all services**
3. **Enable SSL/TLS for all connections**
4. **Regularly update dependencies**
5. **Monitor application logs for suspicious activity**
6. **Use firewall rules to restrict access**
7. **Implement rate limiting (already configured)**
8. **Keep your Supabase and Brevo credentials secure**

## Backup Strategy

1. **Database Backups**

   - Supabase provides automatic daily backups
   - Configure additional backups if needed

2. **File Backups**

   - Regularly backup the uploads directory
   - Use cloud storage for important files

3. **Configuration Backups**

   - Keep secure copies of your .env file
   - Document any custom configurations

## Support

For issues related to:
- **Supabase**: [Supabase Documentation](https://supabase.com/docs)
- **Brevo**: [Brevo Documentation](https://help.brevo.com/hc/en-us)
- **Application**: Check logs and review this guide
