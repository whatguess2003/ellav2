# 🏨 Ella Voice Assistant - Hotel Booking System

## 🎯 Project Overview

**Ella** is an advanced AI-powered voice assistant specifically designed for hotel booking and customer service. Built with cutting-edge LLM technology, it provides seamless hotel search, booking, and check-in verification through voice calls and WhatsApp integration.

## ✨ Key Features

### 🗣️ **Multi-Channel Voice Assistant**
- **Phone Calls**: Natural voice conversations in Malay/English
- **WhatsApp Integration**: Text and voice message support
- **Unified Guest Identity**: Phone number = Guest ID across all channels

### 🏨 **Complete Hotel Management System**
- **Real-time Hotel Search**: City-based search with availability checking
- **Dynamic Pricing**: Date-specific room inventory and pricing
- **Instant Booking**: Voice-activated room reservations
- **Check-in Verification**: Secure phone-based check-in authentication

### 🆔 **Self-Describing Booking References**
Revolutionary booking reference system that contains all booking information:
```
+60123456789;marinacourt;checkin21052025;checkout22052025+deluxesea+withbreakfast+booking1
```
- **📱 Phone**: +60123456789 (Guest ID)
- **🏨 Hotel**: marinacourt (Marina Court)
- **📅 Dates**: Check-in 21/05/2025, Check-out 22/05/2025
- **🛏️ Room**: deluxesea (Deluxe Sea View)
- **✨ Services**: withbreakfast
- **#️⃣ Sequence**: booking1

### 🗄️ **Human-Readable Database Schema**
- **Geographic Hierarchy**: Malaysia → States → Cities → Hotels
- **LLM-Friendly IDs**: `marina-court-kota-kinabalu_deluxe-sea`
- **Raw Name Primary Keys**: Uses actual names instead of codes
- **Self-Documenting**: No lookup required to understand data

## 🏗️ Architecture

### Core Components
```
📞 Voice Interface (ElevenLabs + OpenAI GPT-4o-mini-transcribe)
├── 🤖 LangGraph Agent (OpenAI GPT-4)
├── 🗄️ SQLite Hotel Database (Human-readable schema)
├── 🔄 Redis Session Management
└── 🌐 FastAPI REST API
```

### Database Structure
```
Malaysia (Country)
├── Kuala Lumpur (State)
│   └── Kuala Lumpur (City)
│       └── grand-hyatt-kuala-lumpur (Hotel)
│           ├── grand-hyatt_grand-king (Room Type)
│           └── grand-hyatt_twin-city (Room Type)
└── Sabah (State)
    └── Kota Kinabalu (City)
        └── marina-court-kota-kinabalu (Hotel)
            ├── marina-court_deluxe-sea (Room Type)
            └── marina-court_superior-garden (Room Type)
```

## 🚀 Current Status

### ✅ **Completed Features**
- **🏗️ Database Schema**: Complete 8-table hotel database
- **🏨 Hotel Onboarding**: Add hotels with duplicate prevention
- **📅 Inventory Management**: Date-specific availability and pricing
- **📝 Booking System**: Self-describing booking references
- **🔍 Hotel Search**: Natural language search with filters
- **🗣️ Voice Interface**: Working voice commands and responses
- **🤖 AI Agent**: LangGraph-powered conversational AI
- **📱 Guest ID System**: Phone number as unified customer identity

### 🧪 **Test Data**
- **4 Hotels**: Grand Hyatt KL, Marina Court KK, Shangri-La Penang, Budget Inn JB
- **6 Room Types**: Various categories (King, Twin, Sea View, City View)
- **30 Days Inventory**: Fully populated availability and pricing
- **3 Sample Bookings**: Working booking references and check-in flow

## 🎯 **Unique Innovations**

### 1. **Self-Describing Booking References**
Unlike traditional cryptic booking codes, our references contain all booking information:
- **Traditional**: `ABC123DEF` (meaningless without database lookup)
- **Ella**: `+60123456789;marinacourt;checkin21052025;checkout22052025+deluxesea+withbreakfast+booking1`

### 2. **Unified Guest Identity**
- **Same phone number** for booking, check-in, and customer service
- **Cross-channel continuity** between voice calls and WhatsApp
- **Instant recognition** by AI assistant

### 3. **Human-Readable Database**
- **Property IDs**: `marina-court-kota-kinabalu` (not `PROP001`)
- **Room Type IDs**: `marina-court_deluxe-sea` (not `RT001_DEL`)
- **LLM-optimized** for AI understanding and processing

## 📁 Project Structure

```
ellav2/
├── 🗄️ database/
│   ├── schema.py              # Database schema creation
│   ├── onboarding.py          # Hotel onboarding system
│   └── manage_availability.py # Inventory & booking management
├── 🛠️ tools/
│   └── hotel_search_tool.py   # LangGraph hotel search tools
├── 🧪 test_*.py              # Test scripts and validation
├── 📝 main_with_sql_integration.py # Main API server
├── 🗃️ ella.db               # SQLite hotel database
└── 📋 README.md              # This file
```

## 🔧 Installation & Setup

### Prerequisites
- Python 3.11+
- OpenAI API key
- ElevenLabs API key (for voice)
- Redis server

### Quick Start
```bash
# 1. Clone and setup
git clone <repository>
cd ellav2
pip install -r requirements.txt

# 2. Create database
python database/schema.py

# 3. Add test hotels
python test_hotel_setup.py

# 4. Start the API server
python main_with_sql_integration.py
```

## 🎬 Demo Usage

### Voice Commands (Natural Language)
```
🗣️ "Hello, hotel dekat KL ade tak?"
🤖 "Ada satu hotel yang sesuai di Kuala Lumpur..."

🗣️ "Nak tahu lebih lanjut"
🤖 "Grand Hyatt Kuala Lumpur, 5 bintang..."

🗣️ "Book Grand King Room untuk esok"
🤖 "Booking confirmed! Reference: +60123456789;grandhyatt;..."
```

### Check-in Flow
```
🚗 Guest arrives at hotel
🏨 Reception: "Please call Ella to check-in"
📞 Guest calls from: +60123456789
🤖 Ella: "Hello! Ready to check in to Marina Court, Deluxe Sea View?"
✅ Check-in approved instantly
```

## 🔮 Future Development

### Phase 1: WhatsApp Integration
- Direct WhatsApp Business API integration
- Multi-media message support
- Automated customer service

### Phase 2: Advanced Features
- Multi-language support (Mandarin, Tamil)
- Payment gateway integration
- Loyalty program management

### Phase 3: Scale & Analytics
- Multi-hotel chain support
- Advanced analytics and reporting
- Predictive pricing algorithms

## 🏆 Technical Achievements

✅ **Revolutionary booking reference system** - self-describing and human-readable  
✅ **Unified guest identity** - one phone number across all channels  
✅ **Human-readable database schema** - LLM-optimized for AI processing  
✅ **Natural language processing** - conversational hotel booking in Malay/English  
✅ **Real-time inventory management** - dynamic pricing and availability  
✅ **Secure check-in verification** - phone-based authentication system  

## 📞 Contact & Support

Built with ❤️ for the future of hospitality technology.

---
**🎯 Status**: Production-ready hotel booking system with voice AI integration