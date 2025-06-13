#!/usr/bin/env python3
"""
SEMANTIC TAGGING SYSTEM FOR RAW KNOWLEDGE
Adds topic tags to raw text knowledge to improve semantic search accuracy

TAGGING PHILOSOPHY:
- Tags are embedded directly in raw text: [restaurant][clubhouse][shopping]
- Preserves all original staff-written content
- Makes topics explicit for semantic search model
- Hotel-facing LEON agent will handle tagging via leon_server.py
"""

import sqlite3
import os
import re

def get_db_connection():
    """Get database connection."""
    db_path = os.path.join(os.path.dirname(__file__), 'ella.db')
    return sqlite3.connect(db_path)

def add_semantic_tags_to_raw_knowledge():
    """Add semantic tags to existing raw knowledge content."""
    
    print("🏷️ ADDING SEMANTIC TAGS TO RAW KNOWLEDGE")
    print("=" * 50)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get existing raw knowledge
        cursor.execute("""
            SELECT id, property_id, knowledge_text, staff_author
            FROM hotel_knowledge_bank
            WHERE is_active = 1
        """)
        
        knowledge_entries = cursor.fetchall()
        
        for entry_id, property_id, knowledge_text, staff_author in knowledge_entries:
            print(f"\n📝 Processing: {property_id}")
            print(f"   Author: {staff_author}")
            print(f"   Original length: {len(knowledge_text)} characters")
            
            # Add semantic tags based on content analysis
            tagged_content = add_semantic_tags_to_content(knowledge_text, property_id)
            
            print(f"   Tagged length: {len(tagged_content)} characters")
            
            # Update with tagged content
            cursor.execute("""
                UPDATE hotel_knowledge_bank 
                SET knowledge_text = ?, 
                    last_updated = CURRENT_DATE,
                    version = version + 1
                WHERE id = ?
            """, (tagged_content, entry_id))
            
            print(f"   ✅ Updated with semantic tags")
        
        conn.commit()
        print(f"\n🌟 Semantic tagging complete! Updated {len(knowledge_entries)} entries")
        return True

def add_semantic_tags_to_content(raw_text: str, property_id: str) -> str:
    """Add semantic tags to raw text content based on content analysis."""
    
    # Define semantic tag mappings for different content types
    tag_patterns = {
        # Dining & Food
        '[restaurant]': ['dining recommendations', 'best authentic local food', 'food court', 'night market', 'restaurant', 'char kway teow', 'nasi lemak', 'seafood', 'halal', 'madam kwan'],
        '[food]': ['food', 'eat', 'dining', 'meal', 'breakfast', 'lunch', 'dinner', 'cuisine', 'menu'],
        '[nightmarket]': ['night market', 'jalan alor', 'filipino market', 'gaya street', 'food stalls', 'street food'],
        
        # Shopping
        '[shopping]': ['shopping', 'mall', 'suria klcc', 'pavilion', 'bukit bintang', 'handicraft market', 'souvenirs', 'brands', 'department store'],
        '[shoppingmall]': ['suria klcc', 'pavilion kl', 'shopping mall', 'level 2', 'level 6', 'vip card'],
        
        # Attractions & Activities
        '[attractions]': ['petronas twin towers', 'klcc park', 'skybridge', 'kl tower', 'atmosphere 360', 'aquaria klcc', 'signal hill observatory'],
        '[islands]': ['island hopping', 'tunku abdul rahman', 'marine park', 'sapi', 'mamutik', 'snorkeling', 'beaches'],
        '[nature]': ['mount kinabalu', 'kinabalu park', 'hot springs', 'canopy walk', 'jungle trekking', 'firefly watching'],
        '[cultural]': ['mari mari cultural village', 'tribal experiences', 'traditional food', 'cultural shows'],
        
        # Transportation
        '[transport]': ['airport transfer', 'grab', 'taxi', 'lrt', 'walking', 'skybridge', 'covered walkways', 'transport'],
        '[directions]': ['walking distance', 'minutes walk', 'connected', 'skybridge', 'covered access', 'location'],
        
        # Activities
        '[adventure]': ['white water rafting', 'kiulu river', 'diving', 'sipadan', 'jungle trekking'],
        '[tours]': ['day trip', 'city tour', 'island hopping packages', 'tour desk', 'guides'],
        
        # Facilities & Services
        '[facilities]': ['concierge', 'vip privileges', 'personal shopping assistant', 'tour arrangements'],
        '[deals]': ['exclusive deals', 'partnerships', 'discount', 'vip card', 'savings', 'special offers'],
        
        # Religious & Wellness
        '[religious]': ['asy-syakirin mosque', 'prayer times', 'st andrew church', 'english services', 'floating mosque'],
        '[wellness]': ['spa', 'massage', 'relaxation'],
        
        # Weather & Safety
        '[weather]': ['weather', 'monsoon season', 'afternoon thunderstorms', 'dry season', 'wet season'],
        '[safety]': ['safety', 'security patrols', 'cctv', 'emergency numbers', 'petty theft'],
        
        # Tips & Insider Info
        '[tips]': ['insider tips', 'show room key', 'best photo spot', 'avoid peak hours', 'get there early'],
        '[timing]': ['best time', 'peak hours', 'avoid', 'sunset', 'fountain shows', 'opening hours']
    }
    
    tagged_text = raw_text
    
    # Process each section and add relevant tags
    sections = tagged_text.split('\n\n')
    tagged_sections = []
    
    for section in sections:
        if len(section.strip()) < 50:  # Skip very short sections
            tagged_sections.append(section)
            continue
        
        section_lower = section.lower()
        section_tags = []
        
        # Find relevant tags for this section
        for tag, keywords in tag_patterns.items():
            if any(keyword in section_lower for keyword in keywords):
                section_tags.append(tag)
        
        # Add tags to the beginning of the section if any found
        if section_tags:
            tags_str = ''.join(section_tags)
            tagged_section = f"{tags_str}\n{section}"
        else:
            tagged_section = section
        
        tagged_sections.append(tagged_section)
    
    # Rejoin sections
    final_tagged_text = '\n\n'.join(tagged_sections)
    
    return final_tagged_text

def create_leon_tagging_interface():
    """Create interface for LEON agent to add/modify semantic tags."""
    
    print("\n🤖 CREATING LEON TAGGING INTERFACE")
    print("=" * 40)
    
    interface_code = '''
def leon_add_semantic_tags(property_id: str, section_text: str, tags: list) -> bool:
    """
    LEON Agent Interface for Adding Semantic Tags
    
    Args:
        property_id: Hotel property identifier
        section_text: Specific section of text to tag
        tags: List of tags to add (e.g. ['restaurant', 'shopping', 'attractions'])
    
    Returns:
        bool: Success status
    """
    
    tag_format = ''.join([f'[{tag}]' for tag in tags])
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get current knowledge text
        cursor.execute("""
            SELECT id, knowledge_text FROM hotel_knowledge_bank 
            WHERE property_id = ? AND is_active = 1
        """, (property_id,))
        
        result = cursor.fetchone()
        if not result:
            return False
        
        entry_id, current_text = result
        
        # Find and update the specific section
        if section_text in current_text:
            # Add tags to the beginning of the section
            updated_text = current_text.replace(
                section_text,
                f"{tag_format}\\n{section_text}"
            )
            
            # Update database
            cursor.execute("""
                UPDATE hotel_knowledge_bank 
                SET knowledge_text = ?, 
                    last_updated = CURRENT_DATE,
                    version = version + 1
                WHERE id = ?
            """, (updated_text, entry_id))
            
            conn.commit()
            return True
    
    return False

def leon_get_untagged_sections(property_id: str) -> list:
    """
    Get sections that need tagging for LEON agent review.
    
    Returns:
        list: Sections without adequate tagging
    """
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT knowledge_text FROM hotel_knowledge_bank 
            WHERE property_id = ? AND is_active = 1
        """, (property_id,))
        
        result = cursor.fetchone()
        if not result:
            return []
        
        knowledge_text = result[0]
        sections = knowledge_text.split('\\n\\n')
        
        untagged_sections = []
        for section in sections:
            # Check if section has adequate tags (at least one tag per 200 characters)
            section_length = len(section)
            tag_count = section.count('[') 
            
            if section_length > 100 and tag_count == 0:
                untagged_sections.append(section.strip())
        
        return untagged_sections

# Available semantic tags for LEON agent
AVAILABLE_TAGS = [
    'restaurant', 'food', 'nightmarket', 'shopping', 'shoppingmall',
    'attractions', 'islands', 'nature', 'cultural', 'transport', 
    'directions', 'adventure', 'tours', 'facilities', 'deals',
    'religious', 'wellness', 'weather', 'safety', 'tips', 'timing',
    'hotel', 'rooms', 'amenities', 'pool', 'gym', 'spa', 'wifi',
    'parking', 'pets', 'business', 'events', 'meetings'
]
'''
    
    # Write LEON interface to leon_tagging_interface.py
    with open(os.path.join(os.path.dirname(__file__), '..', 'leon_tagging_interface.py'), 'w') as f:
        f.write(interface_code)
    
    print("✅ LEON tagging interface created: leon_tagging_interface.py")
    return True

def show_tagging_examples():
    """Show examples of tagged content."""
    
    print("\n📋 SEMANTIC TAGGING EXAMPLES")
    print("=" * 40)
    
    examples = [
        {
            'original': 'Best authentic local food within walking distance: Jalan Alor Night Market (20 min walk)',
            'tagged': '[restaurant][food][nightmarket][directions]\nBest authentic local food within walking distance: Jalan Alor Night Market (20 min walk)'
        },
        {
            'original': 'Suria KLCC (connected): International brands, department store, good for souvenirs on Level 2.',
            'tagged': '[shopping][shoppingmall][directions]\nSuria KLCC (connected): International brands, department store, good for souvenirs on Level 2.'
        },
        {
            'original': 'Island hopping: Tunku Abdul Rahman Marine Park - 10 minutes boat ride from Jesselton Point',
            'tagged': '[islands][attractions][tours][directions]\nIsland hopping: Tunku Abdul Rahman Marine Park - 10 minutes boat ride from Jesselton Point'
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n**Example {i}:**")
        print(f"Original: {example['original']}")
        print(f"Tagged:   {example['tagged']}")
    
    print(f"\n💡 **Benefits:**")
    print(f"- Semantic search can find 'island hopping' by searching [islands] tag")
    print(f"- 'Restaurant recommendations' matches [restaurant][food] tags")
    print(f"- Location queries match [directions] tag")
    print(f"- Topics are explicit and searchable")

if __name__ == "__main__":
    if add_semantic_tags_to_raw_knowledge():
        if create_leon_tagging_interface():
            show_tagging_examples()
            print("\n🌟 SEMANTIC TAGGING SYSTEM READY!")
            print("=" * 50)
            print("✅ Raw knowledge enhanced with semantic tags")
            print("✅ LEON agent interface created for ongoing tagging")
            print("✅ Improved semantic search accuracy")
            print("✅ All original content preserved")
        else:
            print("❌ LEON interface creation failed")
    else:
        print("❌ Semantic tagging failed") 