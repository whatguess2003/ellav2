# Main tools imports
from .discovery_agent import DISCOVERY_AGENT_TOOLS
from .room_intelligence_agent import ROOM_INTELLIGENCE_AGENT_TOOLS
from .hotel_intelligence_agent import hotel_intelligence_agent_tool
from .service_agent import SERVICE_AGENT_TOOLS
from .booking_agent import BOOKING_AGENT_TOOLS
from .search_tools.hotel_search_tool import identify_hotel, HOTEL_SEARCH_TOOLS

# Import booking management tools directly from booking_tools
try:
    from .booking_tools.booking_management import confirm_booking, check_booking_status, cancel_booking, get_guest_bookings, modify_booking
    BOOKING_MANAGEMENT_TOOLS = [confirm_booking, check_booking_status, cancel_booking, get_guest_bookings, modify_booking]
    print("Booking management tools loaded successfully")
except ImportError as e:
    BOOKING_MANAGEMENT_TOOLS = []
    print(f"Booking management tools not available: {e}")

# Legacy files removed - functionality covered by specialized agents
# - concierge_agent.py → Hotel Intelligence Agent
# - concierge_intelligence.py → Room Intelligence Agent  
# - advanced_hotel_search.py → Discovery Agent

# Import cloud media sharing tools
try:
    from .media_sharer import CLOUD_MEDIA_TOOLS
    MEDIA_SHARING_TOOLS = CLOUD_MEDIA_TOOLS
    print("✅ Cloud media sharing tools loaded successfully")
except ImportError as e:
    MEDIA_SHARING_TOOLS = []
    print(f"⚠️  Cloud media sharing tools not available: {e}")

# Enhanced tools list with AGENT WORKFLOW ARCHITECTURE priority
ALL_CHAT_TOOLS = (
    DISCOVERY_AGENT_TOOLS +         # 🔍 Discovery Agent - Hotel Finder Expert (agent_workflow.md)
    ROOM_INTELLIGENCE_AGENT_TOOLS + # 🛏️ Room Intelligence Agent - Room Expert (agent_workflow.md)
    [hotel_intelligence_agent_tool] + # 🏨 Hotel Intelligence Agent - Hotel Expert (agent_workflow.md)
    SERVICE_AGENT_TOOLS +           # 🍽️ Service Agent - Service Expert (agent_workflow.md)
    BOOKING_AGENT_TOOLS +           # 📋 Booking Agent - Booking Orchestrator (agent_workflow.md)
    HOTEL_SEARCH_TOOLS +            # 🔍 Hotel search and discovery tools
    BOOKING_MANAGEMENT_TOOLS +      # 📋 Direct booking management tools
    MEDIA_SHARING_TOOLS             # 📸 Media sharing
)

print(f"🔧 Enhanced chat tools: {len(ALL_CHAT_TOOLS)} (with agent workflow architecture)")
print("🎯 AGENT WORKFLOW ARCHITECTURE:")
print(f"   • {DISCOVERY_AGENT_TOOLS[0].name} (DISCOVERY AGENT - Hotel Finder Expert)")
print(f"   • {ROOM_INTELLIGENCE_AGENT_TOOLS[0].name} (ROOM INTELLIGENCE AGENT - Room Expert)")
print(f"   • {hotel_intelligence_agent_tool.name} (HOTEL INTELLIGENCE AGENT - Hotel Expert)")
print(f"   • {SERVICE_AGENT_TOOLS[0].name} (SERVICE AGENT - Service Expert)")
print(f"   • {BOOKING_AGENT_TOOLS[0].name} (BOOKING AGENT - Booking Orchestrator)")

print("🔍 SEARCH & DISCOVERY TOOLS:")
for tool in HOTEL_SEARCH_TOOLS:
    print(f"   • {tool.name}")

print("📋 BOOKING MANAGEMENT TOOLS:")
for tool in BOOKING_MANAGEMENT_TOOLS:
    print(f"   • {tool.name}")

if MEDIA_SHARING_TOOLS:
    print("📸 MEDIA TOOLS:")
    for tool in MEDIA_SHARING_TOOLS:
        print(f"   • {tool.name}")

print("\n✅ Complete Agent Workflow Architecture - Proper separation of concerns!")
print("🔍 Search tools: Hotel discovery and availability checking")
print("📋 Booking tools: Reservation management and confirmation")
print("🎯 Booking Agent: Orchestrates the complete booking workflow")
