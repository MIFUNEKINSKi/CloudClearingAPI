# 🛰️ Google Earth Engine Setup Guide

## Quick Setup for CloudClearingAPI

### 1. **Create Google Cloud Project** (5 minutes)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "New Project" 
3. Name it something like "cloudclearing-indonesia"
4. Note your **Project ID** (e.g., `cloudclearing-indonesia-123456`)

### 2. **Enable Earth Engine API** (2 minutes)

1. In your GCP project, go to [APIs & Services](https://console.cloud.google.com/apis/dashboard)
2. Click "Enable APIs and Services"
3. Search for "**Earth Engine API**"
4. Click it and press "Enable"

### 3. **Set up Billing** (3 minutes)

Even for free usage, GCP requires a billing account:

1. Go to [Billing](https://console.cloud.google.com/billing) 
2. Create billing account (won't be charged for normal EE usage)
3. Link it to your project

### 4. **Authenticate Earth Engine** (2 minutes)

From your CloudClearingAPI directory:

```bash
# Activate your virtual environment
source .venv/bin/activate  # or: .venv/Scripts/activate on Windows

# Authenticate with Earth Engine
earthengine authenticate
```

This opens your browser → log in with Google → copy/paste the token.

### 5. **Update Configuration** (1 minute)

Edit `config/config.yaml`:

```yaml
# Replace 'null' with your actual project ID
gee_project: "cloudclearing-indonesia-123456"  # Your project ID here
```

### 6. **Test the Setup**

```bash
# Test Earth Engine connection
python -c "import ee; ee.Initialize(project='cloudclearing-indonesia-123456'); print('✅ Earth Engine working!')"
```

---

## 🎯 **Result**

After this setup:
- ✅ No more "no project found" errors
- ✅ No more 403 Forbidden warnings  
- ✅ Full satellite imagery access
- ✅ All CloudClearingAPI features enabled

---

## 🔧 **Troubleshooting**

### "Project not found"
- Double-check your project ID in `config.yaml`
- Make sure Earth Engine API is enabled for that project

### "Permission denied" 
- Run `earthengine authenticate` again
- Make sure you're logged into the same Google account that owns the GCP project

### "Billing required"
- Add a billing account to your GCP project
- Don't worry - normal Earth Engine usage is free within quotas

---

## 🚀 **Ready to Monitor Indonesia!**

Once set up, your CloudClearingAPI can:
- Access Sentinel-2 satellite imagery
- Monitor all 10 regions across Java, Sumatra, and Bali  
- Run automated change detection
- Discover overlooked development areas

**Total setup time: ~15 minutes** ⏱️