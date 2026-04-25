# GitHub Upload Guide - Files to Exclude

## Files to NEVER Upload to GitHub

### **Critical Security Files** (Already in .gitignore)
- `.env` - Contains database credentials and secret keys
- `.env.local` - Local environment variables
- `*.json` - Local data files (now using PostgreSQL)

### **Development Files** (Now in .gitignore)
- `*_old.html` - Backup versions of templates
- `*_new.html` - Development versions
- `*_backup.*` - Any backup files
- `test_*` - Test files
- `temp_*` - Temporary files

### **Database Files** (Now in .gitignore)
- `*.db` - SQLite database files
- `*.sqlite` - SQLite database files
- `database_backup_*` - Database backups
- `export_*` - Data export files

### **System Files** (Now in .gitignore)
- `__pycache__/` - Python cache files
- `*.log` - Log files
- `logs/` - Log directory
- `.DS_Store` - macOS system files
- `Thumbs.db` - Windows thumbnail cache

## Files to EXCLUDE from Your Upload

Based on your current directory, **DO NOT upload these files:**

```
clients.json          # Local data file
messages.json         # Local data file  
projects.json         # Local data file
services.json         # Local data file
users.json            # Local data file
templates/projects_old.html   # Old backup file
__pycache__/          # Python cache
```

## Files YOU SHOULD Upload

### **Core Application Files**
```
server_post.py        # Main Flask application
requirements.txt      # Python dependencies
render.yaml          # Render deployment config
build.sh             # Build script
start.sh             # Start script
wsgi.py              # WSGI entry point
runtime.txt          # Python version
Procfile             # Process configuration
```

### **Template Files**
```
templates/base.html
templates/index.html
templates/login.html
templates/register.html
templates/client_dashboard.html
templates/admin_dashboard.html
templates/projects.html      # Your renovated page
templates/client_feedback.html
templates/client_order.html
templates/clients.html
```

### **Static Files**
```
static/app.js         # JavaScript functionality
static/style.css      # Styles (if exists)
```

### **Configuration Files**
```
.env.example         # Environment variables template
.gitignore           # Git ignore rules
DEPLOYMENT_GUIDE.md  # Deployment documentation
README.md            # Project documentation
```

### **Database Tools** (Optional - Keep for local development)
```
database_manager.py  # Database management tool
edit_database.py     # Database editing tool
view_database.py     # Database viewing tool
```

## Quick Upload Checklist

### **Before Uploading:**
1. **Create .env file** (local only, don't upload):
   ```bash
   FLASK_ENV=production
   FLASK_SECRET_KEY=your-super-secret-key-here
   DATABASE_URL=postgresql://username:password@host:port/database
   ```

2. **Remove local data files** (or ensure they're in .gitignore):
   ```bash
   # These should be ignored by .gitignore
   rm *.json
   rm templates/*_old.html
   ```

3. **Install Git** (if not installed):
   ```bash
   winget install Git.Git
   ```

### **Upload Process:**
```bash
# Initialize repository
cd "c:\Users\user\Documents\Personal App"
git init
git add .
git commit -m "Initial deployment: Personal App with renovated projects page"

# Add GitHub remote
git remote add origin https://github.com/yourusername/personal-app.git

# Push to GitHub
git push -u origin main
```

### **What Will Be Uploaded:**
- All core application files
- Your renovated projects.html page
- All templates (except old versions)
- Static files
- Configuration files
- Documentation

### **What Will Be Excluded:**
- All .json data files
- All backup files
- All cache files
- Environment variables
- Local configuration

## Security Reminders

1. **Never upload .env files** - Contains sensitive credentials
2. **Never upload database files** - Contains user data
3. **Never upload local data files** - Should use PostgreSQL
4. **Always check .gitignore** before committing
5. **Review commit history** before pushing

## Deployment Ready Files

Your repository will be deployment-ready with these files:
- Flask application with all routes
- Renovated projects page with modern UI
- Complete template system
- Database management tools
- Render deployment configuration
- Comprehensive documentation

The excluded files are either:
- Security risks (credentials, data)
- Development artifacts (cache, backups)
- Local configuration files

This ensures your GitHub repository is clean, secure, and deployment-ready!
