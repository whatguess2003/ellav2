# Azure Environment Variables Setup

## Required Environment Variables for Azure App Service

Go to **Azure Portal** → **App Service** → **ELLA** → **Configuration** → **Application settings**

Add these environment variables:

### 🔑 REQUIRED API KEYS

```
OPENAI_API_KEY = sk-your-openai-api-key-here
```

### 📱 WhatsApp Business API

```
WHATSAPP_ACCESS_TOKEN = EAAKeTs5E0f0BO10zbgQ9ZBhf1NezsZBMAV5QQqx8e3ZARkYe2zBwaPWDUvEqR4Mb4Kph9yEzs1UAG5J2ZCGOYVLZCjzSDBBkZdR30Hza6ppsR
WHATSAPP_PHONE_NUMBER_ID = 690397460822060
WHATSAPP_BUSINESS_ACCOUNT_ID = 1399209934739284
WHATSAPP_VERIFY_TOKEN = ella_verify_token_2024
WHATSAPP_API_VERSION = v22.0
```

### ☁️ AWS S3 (Optional - for media storage)

```
AWS_ACCESS_KEY_ID = your-aws-access-key
AWS_SECRET_ACCESS_KEY = your-aws-secret-key
AWS_REGION = ap-southeast-1
AWS_BUCKET_NAME = ella-hotel-media
```

### 🎤 ElevenLabs (Optional - for voice)

```
ELEVENLABS_API_KEY = your-elevenlabs-api-key
ELEVENLABS_VOICE_ID = UcqZLa941Kkt8ZhEEybf
```

### 🗄️ Database & Storage

```
DATABASE_PATH = ella_hotel_assistant.db
REDIS_URL = redis://localhost:6379/0
MONGO_URI = mongodb://localhost:27017
MONGO_DB = ella_db
```

### 🤖 Fine-tuned Models (Optional)

```
ELLA_FINETUNED_MODEL = ft:gpt-4o-mini-2024-07-18:inapsolutions:ella-demo-v1:BexmNtfD
```

## 🚀 How to Set in Azure

1. **Go to Azure Portal**: https://portal.azure.com
2. **Find your App Service**: ELLA
3. **Configuration** → **Application settings**
4. **+ New application setting** for each variable above
5. **Save** the configuration
6. **Restart** your App Service

## ✅ Test Your Deployment

After setting the variables, test:

```
https://ella-dvb7arf2f5dtftab.centralus-01.azurewebsites.net/health
```

Should return:
```json
{
  "status": "healthy",
  "service": "ella_guest_assistant",
  "access_level": "READ_ONLY"
}
``` 