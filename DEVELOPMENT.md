# ELLA Development Workflow

## 🎯 **The Challenge**
- **Azure Production**: Uses lightweight `requirements.txt` (optimized for fast deployment)
- **Local Development**: Needs full dependencies for testing and development

## 🛠️ **Local Development Setup**

### **1. Install Development Dependencies**
```bash
# Install full development environment
pip install -r requirements-dev.txt

# Or use the setup script
python dev_setup.py
```

### **2. Environment Variables**
```bash
# Create your local environment file
cp .env.template .env

# Edit .env with your actual API keys
# OPENAI_API_KEY=sk-your-actual-key
# WHATSAPP_ACCESS_TOKEN=your-actual-token
```

### **3. Test Your Setup**
```bash
# Test all imports
python dev_setup.py  # Choose option 2

# Or manually test
python -c "from main import app; print('✅ Main app imports successfully')"
```

### **4. Run Local Server**
```bash
# Using the setup script
python dev_setup.py  # Choose option 4

# Or manually
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

## 🚀 **Development Workflow**

### **Adding New Code**

1. **Develop Locally**
   ```bash
   # Make sure you have dev dependencies
   pip install -r requirements-dev.txt
   
   # Start local server with hot reload
   uvicorn main:app --reload --port 8001
   ```

2. **Test New Features**
   ```bash
   # Test imports
   python dev_setup.py
   
   # Test endpoints
   curl http://localhost:8001/health
   ```

3. **Check Azure Compatibility**
   ```bash
   # Verify your code doesn't use dependencies not in requirements.txt
   python -c "
   import ast
   import sys
   
   # Check if your new code imports anything not in requirements.txt
   # This is a simple check - you can enhance it
   "
   ```

4. **Deploy to Azure**
   ```bash
   git add .
   git commit -m "Add new feature"
   git push origin main
   ```

### **Managing Dependencies**

**For Local Development:**
- Add to `requirements-dev.txt`
- Install with `pip install -r requirements-dev.txt`

**For Azure Production:**
- Only add essential dependencies to `requirements.txt`
- Keep it lightweight to avoid deployment timeouts
- Test compatibility before adding

### **Common Development Tasks**

**Testing WhatsApp Integration:**
```bash
# 1. Install dev dependencies
pip install -r requirements-dev.txt

# 2. Set environment variables in .env
WHATSAPP_ACCESS_TOKEN=your-token
WHATSAPP_PHONE_NUMBER_ID=your-id

# 3. Test locally
python -c "from whatsapp_business_api import WhatsAppBusinessAPI; print('✅ WhatsApp ready')"

# 4. Run server and test webhook
uvicorn main:app --reload --port 8001
# Test: http://localhost:8001/webhook
```

**Testing Chat Assistant:**
```bash
# 1. Make sure you have OpenAI API key in .env
OPENAI_API_KEY=sk-your-key

# 2. Test chat functionality
python -c "from chat_assistant import get_chat_agent; agent = get_chat_agent(); print('✅ Chat agent ready')"

# 3. Test via API
curl -X POST http://localhost:8001/message \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello, I need a hotel room"}'
```

## 🔧 **Troubleshooting**

### **Import Errors**
```bash
# Check what's missing
python dev_setup.py  # Option 2: Test imports

# Install missing packages
pip install package-name

# Add to requirements-dev.txt for future
echo "package-name==version" >> requirements-dev.txt
```

### **Azure Deployment Fails**
```bash
# Check if you added heavy dependencies to requirements.txt
# Move them to requirements-dev.txt instead

# Check for dependency conflicts
pip install -r requirements.txt  # Should work without conflicts
```

### **Local vs Azure Differences**
```bash
# Use environment variables for differences
# Example: Different database URLs, API endpoints, etc.

# In your code:
import os
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///local.db")  # Local default
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")   # Local default
```

## 📋 **File Structure**

```
ellav2/
├── requirements.txt          # Azure production (lightweight)
├── requirements-dev.txt      # Local development (full)
├── dev_setup.py             # Development helper script
├── .env.template            # Environment variables template
├── .env                     # Your actual environment variables (gitignored)
├── main.py                  # Main application
└── DEVELOPMENT.md           # This file
```

## 🎯 **Best Practices**

1. **Always test locally first** before pushing to Azure
2. **Keep requirements.txt minimal** for fast Azure deployments
3. **Use environment variables** for configuration differences
4. **Test imports** before committing new code
5. **Document new dependencies** in both files when needed

## 🚀 **Quick Start Commands**

```bash
# Setup everything
python dev_setup.py

# Daily development
uvicorn main:app --reload --port 8001

# Deploy to Azure
git add . && git commit -m "Update" && git push origin main
``` 