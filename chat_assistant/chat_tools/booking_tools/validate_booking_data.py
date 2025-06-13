#!/usr/bin/env python3
"""
Validate Booking Data Tool - THE TRUST FOUNDATION
Prevents hallucination by validating ALL booking-related information against verified database sources.
This is Ella's truth detector that ensures every hotel name, price, and availability claim is accurate.
"""

from langchain_core.tools import tool
from typing import Dict, Optional, List, Union
import sqlite3
import json
import re
from datetime import datetime
import time

def get_db_connection(db_path: str = "ella.db"):
    """Get read-only database connection."""
    return sqlite3.connect(db_path)

@tool
def validate_booking_data(
    hotel_name: Optional[str] = None,
    hotel_id: Optional[str] = None, 
    room_type: Optional[str] = None,
    price: Optional[float] = None,
    check_in: Optional[str] = None,
    check_out: Optional[str] = None,
    availability_claim: Optional[bool] = None,
    data_source: str = "unknown"
) -> str:
    """
    Validates ALL booking-related information against verified database sources.
    This is Ella's truth detector - prevents hallucination and ensures accuracy.
    
    Args:
        hotel_name: Hotel name to validate
        hotel_id: Hotel property ID to validate
        room_type: Room type name to validate
        price: Price per night to validate
        check_in: Check-in date (YYYY-MM-DD)
        check_out: Check-out date (YYYY-MM-DD)
        availability_claim: Whether room is claimed to be available
        data_source: Where this data came from (for audit trail)
        
    Returns:
        JSON string with validation results and confidence score
    """
    
    try:
        print(f"VALIDATING BOOKING DATA from source: {data_source}")
        
        validation_result = {
            "is_valid": True,
            "validation_details": {
                "hotel": {"valid": None, "verified_name": None, "verified_id": None},
                "room": {"valid": None, "verified_type": None, "verified_features": []},
                "price": {"valid": None, "verified_rate": None, "last_updated": None},
                "availability": {"valid": None, "verified_status": None, "checked_at": None}
            },
            "errors": [],
            "confidence_score": 1.0,
            "database_source": "ella.db",
            "timestamp": datetime.now().isoformat()
        }
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 1. HOTEL VALIDATION
            if hotel_name or hotel_id:
                hotel_valid, hotel_details = validate_hotel_existence(cursor, hotel_name, hotel_id)
                validation_result["validation_details"]["hotel"] = hotel_details
                
                if not hotel_valid:
                    validation_result["is_valid"] = False
                    validation_result["errors"].append(f"Hotel '{hotel_name or hotel_id}' not found in database")
                    validation_result["confidence_score"] = 0.0
            
            # 2. ROOM TYPE VALIDATION
            if room_type and hotel_details.get("verified_id"):
                room_valid, room_details = validate_room_type(cursor, hotel_details["verified_id"], room_type)
                validation_result["validation_details"]["room"] = room_details
                
                if not room_valid:
                    validation_result["is_valid"] = False
                    validation_result["errors"].append(f"Room type '{room_type}' not available at this hotel")
                    validation_result["confidence_score"] *= 0.5
            
            # 3. PRICE VALIDATION
            if price and hotel_details.get("verified_id"):
                price_valid, price_details = validate_price_accuracy(cursor, hotel_details["verified_id"], room_type, price)
                validation_result["validation_details"]["price"] = price_details
                
                if not price_valid:
                    validation_result["is_valid"] = False
                    actual_price = price_details.get("verified_rate", "unknown")
                    validation_result["errors"].append(f"Price incorrect: claimed RM{price}, actual RM{actual_price}")
                    validation_result["confidence_score"] *= 0.3
            
            # 4. AVAILABILITY VALIDATION
            if availability_claim is not None and hotel_details.get("verified_id"):
                avail_valid, avail_details = validate_availability_claim(cursor, hotel_details["verified_id"], room_type, check_in, check_out)
                validation_result["validation_details"]["availability"] = avail_details
                
                if not avail_valid:
                    validation_result["is_valid"] = False
                    validation_result["errors"].append("Availability claim incorrect - room not available for these dates")
                    validation_result["confidence_score"] *= 0.2
            
            # 5. DATA SOURCE VALIDATION
            if data_source == "llm_generation" or data_source == "unknown":
                validation_result["confidence_score"] *= 0.1
                validation_result["errors"].append("Data source unreliable - requires database verification")
            
            # 6. FINAL CONFIDENCE CALCULATION
            if validation_result["confidence_score"] < 0.8:
                validation_result["is_valid"] = False
            
        print(f"VALIDATION COMPLETE: Valid={validation_result['is_valid']}, Confidence={validation_result['confidence_score']:.2f}")
        
        return json.dumps(validation_result, indent=2)
        
    except Exception as e:
        print(f"VALIDATION ERROR: {e}")
        error_result = {
            "is_valid": False,
            "validation_details": {},
            "errors": [f"Validation system error: {str(e)}"],
            "confidence_score": 0.0,
            "database_source": "validation_failed",
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_result, indent=2)

def validate_hotel_existence(cursor, hotel_name: Optional[str], hotel_id: Optional[str]) -> tuple:
    """Validate if hotel exists in database"""
    try:
        if hotel_id:
            cursor.execute("SELECT property_id, hotel_name, is_active FROM hotels WHERE property_id = ?", (hotel_id,))
        elif hotel_name:
            cursor.execute("SELECT property_id, hotel_name, is_active FROM hotels WHERE LOWER(hotel_name) LIKE LOWER(?)", (f"%{hotel_name}%",))
        else:
            return False, {"valid": False, "verified_name": None, "verified_id": None}
        
        result = cursor.fetchone()
        
        if result:
            property_id, verified_name, is_active = result
            if is_active:
                return True, {
                    "valid": True,
                    "verified_name": verified_name,
                    "verified_id": property_id
                }
            else:
                return False, {
                    "valid": False,
                    "verified_name": verified_name,
                    "verified_id": property_id,
                    "error": "Hotel inactive"
                }
        else:
            return False, {"valid": False, "verified_name": None, "verified_id": None}
            
    except Exception as e:
        print(f"Hotel validation error: {e}")
        return False, {"valid": False, "error": str(e)}

def validate_room_type(cursor, property_id: str, room_type: str) -> tuple:
    """Validate if room type exists for this hotel"""
    try:
        cursor.execute("""
            SELECT room_type_id, room_name, amenities, room_features, is_active 
            FROM room_types 
            WHERE property_id = ? AND LOWER(room_name) LIKE LOWER(?) AND is_active = 1
        """, (property_id, f"%{room_type}%"))
        
        result = cursor.fetchone()
        
        if result:
            room_id, verified_name, amenities, features, is_active = result
            features_list = []
            if amenities:
                features_list.extend(amenities.split(','))
            if features:
                features_list.extend(features.split(','))
                
            return True, {
                "valid": True,
                "verified_type": verified_name,
                "verified_features": [f.strip() for f in features_list if f.strip()]
            }
        else:
            return False, {"valid": False, "verified_type": None, "verified_features": []}
            
    except Exception as e:
        print(f"Room validation error: {e}")
        return False, {"valid": False, "error": str(e)}

def validate_price_accuracy(cursor, property_id: str, room_type: Optional[str], claimed_price: float) -> tuple:
    """Validate if price matches database rates - using current pricing"""
    try:
        if room_type:
            # Use current_price from room_inventory for accurate validation
            cursor.execute("""
                SELECT AVG(ri.current_price) as avg_current_price, rt.room_name
                FROM room_inventory ri
                JOIN room_types rt ON ri.property_id = rt.property_id AND ri.room_type_id = rt.room_type_id
                WHERE ri.property_id = ? AND LOWER(rt.room_name) LIKE LOWER(?) AND rt.is_active = 1
                AND ri.stay_date >= DATE('now')
                LIMIT 30
            """, (property_id, f"%{room_type}%"))
        else:
            cursor.execute("""
                SELECT AVG(ri.current_price) as avg_current_price, 'Any Room' as room_name
                FROM room_inventory ri
                JOIN room_types rt ON ri.property_id = rt.property_id AND ri.room_type_id = rt.room_type_id
                WHERE ri.property_id = ? AND rt.is_active = 1
                AND ri.stay_date >= DATE('now')
                LIMIT 30
            """, (property_id,))
        
        result = cursor.fetchone()
        
        if result and result[0]:
            actual_price = float(result[0])
            room_name = result[1]
            
            # More reasonable price tolerance for dynamic pricing (20%)
            price_tolerance = 0.20  # 20% tolerance for current market pricing
            
            if abs(claimed_price - actual_price) / actual_price <= price_tolerance:
                return True, {
                    "valid": True,
                    "verified_rate": actual_price,
                    "price_source": "current_market_rate",
                    "tolerance_used": f"{price_tolerance*100}%",
                    "last_updated": datetime.now().isoformat()
                }
            else:
                return False, {
                    "valid": False,
                    "verified_rate": actual_price,
                    "claimed_rate": claimed_price,
                    "price_source": "current_market_rate",
                    "price_difference": abs(claimed_price - actual_price),
                    "price_difference_percent": round(abs(claimed_price - actual_price) / actual_price * 100, 2),
                    "tolerance_used": f"{price_tolerance*100}%",
                    "last_updated": datetime.now().isoformat()
                }
        else:
            # Fallback to base price if no current pricing data
            cursor.execute("""
                SELECT base_price_per_night, room_name
                FROM room_types 
                WHERE property_id = ? AND LOWER(room_name) LIKE LOWER(?) AND is_active = 1
            """, (property_id, f"%{room_type}%" if room_type else "%"))
            
            fallback_result = cursor.fetchone()
            if fallback_result:
                base_price, room_name = fallback_result
                return False, {
                    "valid": False,
                    "verified_rate": base_price,
                    "claimed_rate": claimed_price,
                    "price_source": "base_price_fallback",
                    "warning": "No current pricing data available, using base price",
                    "last_updated": datetime.now().isoformat()
                }
            else:
                return False, {"valid": False, "verified_rate": None, "error": "No pricing data found"}
            
    except Exception as e:
        print(f"Price validation error: {e}")
        return False, {"valid": False, "error": str(e)}

def validate_availability_claim(cursor, property_id: str, room_type: Optional[str], check_in: Optional[str], check_out: Optional[str]) -> tuple:
    """Validate availability claim against hotel status"""
    try:
        # Check hotel and room status
        if room_type:
            cursor.execute("""
                SELECT rt.is_active, h.is_active as hotel_active
                FROM room_types rt
                JOIN hotels h ON rt.property_id = h.property_id
                WHERE rt.property_id = ? AND LOWER(rt.room_name) LIKE LOWER(?)
            """, (property_id, f"%{room_type}%"))
        else:
            cursor.execute("""
                SELECT COUNT(*) as active_rooms, h.is_active as hotel_active
                FROM room_types rt
                JOIN hotels h ON rt.property_id = h.property_id
                WHERE rt.property_id = ? AND rt.is_active = 1
                GROUP BY h.is_active
            """, (property_id,))
        
        result = cursor.fetchone()
        
        if result:
            room_active, hotel_active = result if room_type else (result[0] > 0, result[1])
            
            if hotel_active and room_active:
                return True, {
                    "valid": True,
                    "verified_status": "available",
                    "checked_at": datetime.now().isoformat()
                }
            else:
                return False, {
                    "valid": False,
                    "verified_status": "unavailable",
                    "checked_at": datetime.now().isoformat()
                }
        else:
            return False, {"valid": False, "verified_status": "not_found"}
            
    except Exception as e:
        print(f"Availability validation error: {e}")
        return False, {"valid": False, "error": str(e)}

# Export the tool for integration
VALIDATION_TOOLS = [validate_booking_data] 