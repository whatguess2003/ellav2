"""
Chat Assistant Main Logic
Uses Langchain AgentExecutor with streamlined tool architecture
"""

import openai
import json
import time
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage
from config.settings import ***REMOVED***, MODEL_CONFIG
from memory.redis_memory import append_dialog_turn, get_dialog_history, get_full_context, get_all_dialog_turns, get_summary, store_summary
from core.guest_id import get_guest_id

# Import streamlined tools
from .chat_tools import ALL_CHAT_TOOLS

def get_chat_system_prompt():
    """Enhanced system prompt for intelligent multi-agent orchestration"""
    return """You are Ella, a knowledgeable Malaysian hotel concierge assistant.

🎯 YOUR ROLE:
You are the guest-facing assistant who provides rich, detailed, conversational responses. You have NO direct knowledge about hotels, rooms, or services - you must gather this information from your specialist agents and then present it beautifully to guests.

🔧 MULTI-AGENT ORCHESTRATION:
When guests ask questions, you may need to call MULTIPLE agents to provide complete answers:

• **discovery_agent_tool** → Hotel search and availability
• **hotel_intelligence_agent_tool** → Hotel facilities, policies, contact info  
• **room_intelligence_agent_tool** → Room details, amenities, pricing
• **service_agent_tool** → Services (breakfast, spa, dining)
• **booking_agent_tool** → Booking operations (only when ready)

🎨 RESPONSE SYNTHESIS STRATEGY:
1. **Identify Information Gaps**: If a guest asks about "hotels in KL", call discovery_agent_tool
2. **Enrich Basic Results**: If discovery returns plain results, call hotel_intelligence_agent_tool and room_intelligence_agent_tool for details
3. **Create Rich Responses**: Combine all agent information into compelling, detailed presentations
4. **Use Guest Language**: Present information conversationally, not as raw data

📝 RESPONSE FORMATTING:
Transform agent data into engaging presentations:
- Use emojis and formatting for visual appeal
- Highlight key features and benefits
- Compare options when multiple hotels/rooms available
- Include specific details (room size, amenities, facilities)
- Mention pricing prominently
- Add practical information (location, contact, policies)

🎯 EXAMPLE ORCHESTRATION:
Guest: "I need room for 2 people in KL tonight"

Step 1: Call discovery_agent_tool → Gets basic hotel list
Step 2: Call hotel_intelligence_agent_tool for each hotel → Gets facilities
Step 3: Call room_intelligence_agent_tool for room details → Gets amenities
Step 4: Synthesize into rich response with details, facilities, room features, pricing

📋 BOOKING READINESS:
Only call booking_agent_tool when context has: hotel + room + dates + pricing discussed AND guest wants to book/confirm/check booking status.

💬 CONVERSATION STYLE:
- Chat naturally like a knowledgeable concierge
- Be enthusiastic about hotel features
- Provide specific, actionable information
- Ask follow-up questions to understand preferences
- Make recommendations based on guest needs

🚫 IMPORTANT:
- NEVER make up hotel information - always get it from agents
- ALWAYS call agents to get current, accurate data
- NEVER provide generic responses - always use specific details from agents
- Call multiple agents in one turn when needed for complete answers."""

def execute_chat_function_call(function_name, arguments):
    """This function is no longer needed with AgentExecutor"""
    pass

def handle_chat_message(message, guest_id=None):
    """Handle chat conversations using Multi-Agent Shared Context orchestration"""
    guest_id = get_guest_id() if guest_id is None else guest_id
    thread_id = f"{guest_id}_chat_thread"
    
    print(f"[CHAT] Processing: '{message}' for {guest_id}")
    
    # MULTI-AGENT SHARED CONTEXT ORCHESTRATION
    from memory.multi_agent_context import (
        get_shared_context, extract_all_intents, determine_active_agent
    )
    
    # Get shared context and extract intents from all agents
    shared_context = get_shared_context(guest_id)
    all_intents = extract_all_intents(message, guest_id)
    active_agent = determine_active_agent(all_intents)
    
    # Update conversation state in shared context
    shared_context.update_section("conversation_state", {
        "current_intent": "multi_agent",
        "active_agent": active_agent,
        "last_user_input": message
    })
    
    print(f"🤝 SHARED CONTEXT: Active agent = {active_agent}")
    print(f"🎯 EXTRACTED INTENTS: {list(all_intents.keys())}")
    
    # Get conversation context BEFORE adding new message
    dialog_history = get_dialog_history(thread_id)
    full_context = get_full_context(guest_id)
    
    # Check if this is a voice handoff scenario
    is_voice_handoff = False
    handoff_context = ""
    
    if dialog_history:
        # Check if last message is assistant message that looks like voice handoff
        last_message = dialog_history[-1]
        if (last_message.get("role") == "assistant" and 
            ("📞 **Voice Call Recap**" in last_message.get("content", "") or
             "voice call" in last_message.get("content", "").lower())):
            is_voice_handoff = True
            handoff_context = last_message.get("content", "")
            print(f"[CHAT] 🔄 VOICE HANDOFF DETECTED - Guest responding to handoff message")
    
    should_summarize = append_dialog_turn(thread_id, "user", message)
    
    # Trigger summarization if needed
    if should_summarize:
        create_guest_profile_summary(guest_id, thread_id)
    
    # Get updated conversation context
    dialog_history = get_dialog_history(thread_id)
    full_context = get_full_context(guest_id)  # Refresh after adding new turn
    
    # Create ChatOpenAI instance with enhanced capacity for rich responses
    llm = ChatOpenAI(
        model=MODEL_CONFIG["chat_assistant"],
        temperature=0.7,
        openai_api_key=***REMOVED***,
        max_tokens=800  # Increased for richer, more detailed responses
    )
    
    # Enhanced system prompt with multi-agent shared context
    system_prompt = get_chat_system_prompt()
    
    # Add simple context status for booking agent routing
    context_data = shared_context.get_context()
    
    # Check if booking context is complete
    booking_ready = (
        context_data['search_context'].get('selected_hotel') and
        context_data['search_context'].get('check_in') and
        context_data['search_context'].get('check_out') and
        context_data['room_context'].get('available_rooms')
    )
    
    system_prompt += f"""

CONTEXT STATUS:
Booking Ready: {'YES' if booking_ready else 'NO - missing: ' + ', '.join([
    'hotel' if not context_data['search_context'].get('selected_hotel') else '',
    'dates' if not (context_data['search_context'].get('check_in') and context_data['search_context'].get('check_out')) else '',
    'room/pricing' if not context_data['room_context'].get('available_rooms') else ''
]).strip(', ')}"""
    
    # Add conversation summary for long-term memory
    if full_context['summary']:
        system_prompt += f"""

👤 GUEST PROFILE:
{full_context['summary']}

Use this guest profile to personalize responses and understand their preferences. This profile is built from all previous conversations."""
    
    if is_voice_handoff:
        system_prompt += f"""

🔄 VOICE HANDOFF CONTEXT:
This conversation was initiated after a voice call handoff. The previous message was ELLA's voice call recap explaining what the guest requested during their phone call.

The guest is now responding to that recap message. Their response should be interpreted in the context of the voice call handoff scenario.

HANDOFF MESSAGE CONTEXT:
{handoff_context[:500]}...

INSTRUCTIONS FOR HANDOFF RESPONSES:
- Guest's message is a continuation of the voice call discussion
- Don't ask for basic info that was covered in the voice recap
- Proceed with the specific scenario mentioned in the handoff (booking, payment, photos, etc.)
- Be natural and assume context from the voice call
- If guest says "yes" or "ok", interpret it as agreement to proceed with the handoff scenario"""

    # Create prompt template with conversation history
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
    
    # Create agent with tools
    agent = create_openai_functions_agent(llm, ALL_CHAT_TOOLS, prompt)
    
    # Create agent executor with enhanced multi-agent orchestration capabilities
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=ALL_CHAT_TOOLS, 
        verbose=True,  # This brings back the detailed logs!
        max_iterations=8,  # Increased to allow complex multi-agent workflows
        return_intermediate_steps=True
    )
    
    try:
        start_time = time.time()
        
        # Convert dialog history to Langchain format
        chat_history = []
        for turn in dialog_history[-10:]:  # Last 10 turns for focused context (was 50!)
            if turn["role"] == "user":
                chat_history.append(HumanMessage(content=turn["content"]))
            elif turn["role"] == "assistant":
                chat_history.append(AIMessage(content=turn["content"]))
        
        # Execute with agent
        result = agent_executor.invoke({
            "input": message,
            "chat_history": chat_history
        })
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        
        assistant_message = result["output"]
        
        print(f"[CHAT] AgentExecutor Response ({response_time:.0f}ms): {len(assistant_message)} chars")
        if is_voice_handoff:
            print(f"[CHAT] 🔄 Voice handoff context applied successfully")
        
        append_dialog_turn(thread_id, "assistant", assistant_message)
        
        return assistant_message
        
    except Exception as e:
        print(f"[CHAT] AgentExecutor Error: {e}")
        error_response = "Sorry, something went wrong. Let me help you find hotels. What are you looking for?"
        append_dialog_turn(thread_id, "assistant", error_response)
        return error_response

class ChatAssistant:
    def __init__(self):
        """Initialize ChatAssistant with AgentExecutor"""
        self.agent_executor = None
        
    def handle_message(self, message, guest_id=None):
        """Handle message using AgentExecutor for multi-tool chaining"""
        result = handle_chat_message(message, guest_id)
        return {"message": result}

def get_chat_agent():
    """Get ChatAssistant instance with multi-tool chaining capabilities"""
    return ChatAssistant()

def create_guest_profile_summary(guest_id, thread_id):
    """Create focused guest profile summary using LLM."""
    try:
        # Get all dialog turns for summarization
        all_turns = get_all_dialog_turns(thread_id)
        if len(all_turns) < 10:  # Don't summarize if too few turns
            return
        
        # Parse dialog turns
        dialog_content = []
        for turn in all_turns:
            dialog_content.append(f"{turn['role']}: {turn['content']}")
        
        dialog_text = "\n".join(dialog_content)
        
        # Create LLM for summarization
        llm = ChatOpenAI(openai_api_key=***REMOVED***, model="gpt-4o", temperature=0.1)
        
        summary_prompt = f"""Extract ONLY guest biography and hotel preferences from this conversation.

Create a concise guest profile focusing on:
1. GUEST BIOGRAPHY: Personal info, travel patterns, background details
2. HOTEL PREFERENCES: Room types, amenities, locations, price range they prefer

Ignore transactional details like specific dates, booking status, or search results.
Build a timeless guest profile that helps understand WHO they are and WHAT they like in hotels.

CONVERSATION:
{dialog_text}

GUEST PROFILE:"""

        response = llm.invoke(summary_prompt)
        new_summary = response.content.strip()
        
        # Append to existing summary if it exists
        existing_summary = get_summary(guest_id)
        if existing_summary:
            combined_summary = f"{existing_summary}\n\n--- UPDATED PROFILE ---\n{new_summary}"
        else:
            combined_summary = new_summary
        
        # Store updated summary
        store_summary(guest_id, combined_summary)
        print(f"📝 GUEST PROFILE UPDATED for {guest_id}: {len(new_summary)} chars")
        
    except Exception as e:
        print(f"❌ Profile summarization failed: {e}") 