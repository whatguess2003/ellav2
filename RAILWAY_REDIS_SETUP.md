# 🚀 Railway Redis Setup Guide

## 📋 **Step-by-Step Redis Configuration**

### **1. Add Redis Service to Railway**

1. **Go to Railway Dashboard**: https://railway.app/dashboard
2. **Open your project**: `web-production-2a2c9`
3. **Click "New Service"** or **"+"** button
4. **Select "Database"** → **"Redis"**
5. **Railway will automatically:**
   - Create Redis instance
   - Generate connection credentials
   - Set environment variables

### **2. Environment Variables (Auto-Generated)**

Railway will automatically create these variables:
```bash
REDIS_URL=redis://default:password@redis.railway.internal:6379
REDIS_HOST=redis.railway.internal
REDIS_PORT=6379
REDIS_PASSWORD=auto_generated_password
```

### **3. Connect Services**

1. **In your web service settings**
2. **Go to "Variables" tab**
3. **Verify these variables are available:**
   - `REDIS_URL`
   - `REDIS_HOST` 
   - `REDIS_PORT`
   - `REDIS_PASSWORD`

### **4. Deploy Changes**

```bash
git add .
git commit -m "Configure Redis for Railway deployment"
git push
```

## 🔧 **Redis Dependencies in ELLA**

### **Core Systems Using Redis:**

1. **Memory System** (`memory/redis_memory.py`)
   - Dialog history storage
   - Session management
   - Context tracking

2. **Multi-Agent Context** (`memory/multi_agent_context.py`)
   - Agent coordination
   - Shared context state

3. **Hotel Search Tools**
   - Search session caching
   - Guest preferences
   - Search history

4. **Voice Hotel Server** (`voice_hotel/server.py`)
   - Real-time session state

5. **Concierge Sessions** (`core/concierge_session.py`)
   - Guest session management

## ✅ **Verification Steps**

### **1. Check Redis Connection**

Add this test endpoint to verify Redis:

```python
@app.get("/test/redis")
async def test_redis():
    try:
        from memory.redis_memory import redis_client
        redis_client.ping()
        return {"status": "Redis connected successfully"}
    except Exception as e:
        return {"status": "Redis connection failed", "error": str(e)}
```

### **2. Test Memory Functions**

```bash
curl https://web-production-2a2c9.up.railway.app/test/redis
```

### **3. Monitor Redis Usage**

- **Railway Dashboard** → **Redis Service** → **Metrics**
- Monitor memory usage, connections, operations

## 🚨 **Troubleshooting**

### **Connection Issues:**

1. **Check environment variables** in Railway dashboard
2. **Verify Redis service is running**
3. **Check network connectivity** between services

### **Memory Issues:**

1. **Monitor Redis memory usage**
2. **Implement TTL** for temporary data
3. **Clear old sessions** periodically

### **Performance Issues:**

1. **Use connection pooling**
2. **Implement Redis clustering** if needed
3. **Monitor query performance**

## 📊 **Expected Benefits**

✅ **Persistent session storage**
✅ **Multi-agent context sharing**
✅ **Fast hotel search caching**
✅ **Scalable memory management**
✅ **Real-time voice session state**

## 🔄 **Migration from Simple Memory**

The system will automatically:
1. **Try Redis connection first**
2. **Fallback to simple memory** if Redis unavailable
3. **Log connection status** for debugging

No code changes needed - the fallback system is already implemented! 