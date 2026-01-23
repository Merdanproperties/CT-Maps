# GitHub Setup Instructions

## ✅ Current Status
- Git repository initialized
- Initial commit created on `main` branch
- `develop` branch created for ongoing development

## 🔗 Connect to GitHub Repository

### Step 1: Add GitHub Remote
```bash
cd "/Users/jacobmermelstein/Desktop/CT Maps"
git remote add origin https://github.com/Merdanproperties/CT-Maps.git
```

### Step 2: Push Main Branch (Production)
```bash
# Make sure you're on main branch
git checkout main

# Push main branch to GitHub
git push -u origin main
```

### Step 3: Push Develop Branch (Development)
```bash
# Switch to develop branch
git checkout develop

# Push develop branch to GitHub
git push -u origin develop
```

## 📋 Branch Workflow

### Working on New Features (Development)
```bash
# Switch to develop branch
git checkout develop

# Make your changes, then commit
git add .
git commit -m "Description of your changes"

# Push to GitHub
git push origin develop
```

### Deploying to Production
When you're ready to deploy features from develop to production:

```bash
# Switch to main branch
git checkout main

# Merge develop into main
git merge develop

# Push to GitHub
git push origin main
```

### Quick Commands Reference

**Check current branch:**
```bash
git branch
```

**Switch branches:**
```bash
git checkout main      # Switch to production
git checkout develop   # Switch to development
```

**View all branches:**
```bash
git branch -a
```

**See what's changed:**
```bash
git status
```

## 🔐 Authentication

If you're prompted for credentials when pushing:
- **Username**: Your GitHub username
- **Password**: Use a Personal Access Token (not your GitHub password)
  - Go to: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
  - Generate a new token with `repo` permissions
  - Use this token as your password

## 🚀 Next Steps

1. Run the commands in Step 1-3 above to connect to GitHub
2. Continue development on the `develop` branch
3. Merge `develop` → `main` when ready for production releases
