-- ELLA Hotel Database Test Script - PostgreSQL Version
-- Run this to verify your PostgreSQL database setup is working correctly

-- Test 1: Check PostgreSQL version
SELECT 'PostgreSQL Version:' as test, version() as result;

-- Test 2: List all tables
SELECT 'Tables Created:' as test, COUNT(*) as result
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('hotels', 'room_types', 'availability', 'bookings', 'guests', 'check_ins', 'payments', 'reviews');

-- Test 3: Count records in each table
SELECT 'Hotels:' as table_name, COUNT(*) as record_count FROM hotels
UNION ALL
SELECT 'Room Types:', COUNT(*) FROM room_types
UNION ALL  
SELECT 'Availability:', COUNT(*) FROM availability
UNION ALL
SELECT 'Guests:', COUNT(*) FROM guests
UNION ALL
SELECT 'Bookings:', COUNT(*) FROM bookings
UNION ALL
SELECT 'Check-ins:', COUNT(*) FROM check_ins
UNION ALL
SELECT 'Payments:', COUNT(*) FROM payments
UNION ALL
SELECT 'Reviews:', COUNT(*) FROM reviews;

-- Test 4: Sample hotel data
SELECT 
    'Sample Hotels:' as test,
    h.name || ' (' || h.city || ') - ' || h.star_rating || '⭐' as hotel_info
FROM hotels h
ORDER BY h.name;

-- Test 5: Room types with pricing
SELECT 
    'Room Types:' as test,
    h.name || ' - ' || rt.name || ' (RM ' || rt.base_price || ')' as room_info
FROM room_types rt
JOIN hotels h ON rt.hotel_id = h.id
ORDER BY h.name, rt.name;

-- Test 6: Availability for next 7 days
SELECT 
    'Next 7 Days Availability:' as test,
    h.name || ' - ' || rt.name || ' on ' || a.date || ' (RM ' || a.price || ', ' || a.available_rooms || ' rooms)' as availability_info
FROM availability a
JOIN room_types rt ON a.room_type_id = rt.id
JOIN hotels h ON rt.hotel_id = h.id
WHERE a.date BETWEEN CURRENT_DATE AND CURRENT_DATE + 6
ORDER BY a.date, h.name
LIMIT 10;

-- Test 7: Sample booking
SELECT 
    'Sample Booking:' as test,
    'Guest: ' || g.name || ', Hotel: ' || h.name || ', Room: ' || rt.name || ', Dates: ' || b.check_in_date || ' to ' || b.check_out_date as booking_info
FROM bookings b
JOIN guests g ON b.guest_id = g.id
JOIN hotels h ON b.hotel_id = h.id
JOIN room_types rt ON b.room_type_id = rt.id
LIMIT 1;

-- Test 8: Check array amenities (PostgreSQL specific)
SELECT 
    'Hotel Amenities:' as test,
    h.name || ' - ' || array_to_string(h.amenities[1:3], ', ') as amenities_sample
FROM hotels h
LIMIT 3;

-- Final success message
SELECT 
    '🎉 Database Test Complete!' as message,
    'Your ELLA hotel PostgreSQL database is ready to use!' as status; 