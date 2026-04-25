#!/bin/bash

# Quick Deploy Script - GitHub & Render
# Run this script to quickly deploy your app

echo "=== Personal App Quick Deploy ==="
echo ""

# Check if Git is installed
if ! command -v git &> /dev/null; then
    echo "Git is not installed. Please install Git first:"
    echo "  Download from: https://git-scm.com/download/win"
    echo "  Or run: winget install Git.Git"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "server_post.py" ]; then
    echo "Error: server_post.py not found. Please run this from the project root."
    exit 1
fi

echo "Step 1: Initializing Git repository..."
if [ ! -d ".git" ]; then
    git init
    echo "Git repository initialized."
else
    echo "Git repository already exists."
fi

echo ""
echo "Step 2: Adding files to Git..."
git add .

echo ""
echo "Step 3: Creating commit..."
git commit -m "Deploy: Personal App with client management system

Features:
- User authentication (admin/client)
- Project management system
- Client messaging
- Feedback system
- Mobile responsive design
- PostgreSQL database integration
- Render deployment ready"

echo ""
echo "Step 4: Checking for GitHub remote..."
if ! git remote get-url origin &> /dev/null; then
    echo "No GitHub remote found."
    echo "Please:"
    echo "1. Create a GitHub repository at https://github.com/new"
    echo "2. Run: git remote add origin https://github.com/yourusername/personal-app.git"
    echo "3. Run: git push -u origin main"
    echo ""
    echo "Then continue with Render deployment:"
    echo "1. Go to https://render.com"
    echo "2. Connect your GitHub repository"
    echo "3. Use render.yaml for configuration"
    exit 0
else
    echo "GitHub remote found."
    echo "Step 5: Pushing to GitHub..."
    git push origin main
fi

echo ""
echo "=== Next Steps ==="
echo "1. Check your GitHub repository"
echo "2. Go to https://render.com"
echo "3. Click 'New +' > 'Web Service'"
echo "4. Connect your GitHub repository"
echo "5. Use these settings:"
echo "   - Name: personal-app"
echo "   - Environment: Python 3"
echo "   - Build Command: bash build.sh"
echo "   - Start Command: bash start.sh"
echo "6. Add environment variables:"
echo "   - FLASK_ENV = production"
echo "   - FLASK_SECRET_KEY = (generate secure key)"
echo "   - DATABASE_URL = (your PostgreSQL connection string)"
echo ""
echo "=== Deployment Ready! ==="
