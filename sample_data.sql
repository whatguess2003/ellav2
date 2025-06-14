-- ELLA Hotel System Sample Data
-- Run this script AFTER database_schema.sql
-- Database: ella_hotel

-- Insert sample hotels
INSERT INTO hotels (name, slug, city, state, address, phone, email, star_rating, description, amenities) VALUES
('Grand Hyatt Kuala Lumpur', 'grand-hyatt-kuala-lumpur', 'Kuala Lumpur', 'Kuala Lumpur', 
 '12 Jalan Pinang, Kuala Lumpur City Centre, 50450 Kuala Lumpur', '+60 3-2182 1234', 
 'kualalumpur.grand@hyatt.com', 5, 
 'Luxury hotel in the heart of Kuala Lumpur with world-class amenities',
 ARRAY['WiFi', 'Pool', 'Gym', 'Spa', 'Restaurant', 'Bar', 'Concierge']),

('Sam Hotel KL', 'sam-hotel-kl', 'Kuala Lumpur', 'Kuala Lumpur',
 '123 Jalan Bukit Bintang, 55100 Kuala Lumpur', '+60 3-2148 8888',
 'info@samhotelkl.com', 3,
 'Comfortable budget hotel in Bukit Bintang area',
 ARRAY['WiFi', 'Restaurant', 'Laundry', '24h Front Desk']),

('Marina Court Resort', 'marina-court-resort', 'Kota Kinabalu', 'Sabah',
 '1 Jalan Tun Fuad Stephens, 88000 Kota Kinabalu, Sabah', '+60 88-237 999',
 'reservations@marinacourt.com', 4,
 'Beachfront resort with stunning sea views and modern facilities',
 ARRAY['WiFi', 'Pool', 'Beach Access', 'Restaurant', 'Spa', 'Water Sports']);

-- Insert room types
INSERT INTO room_types (hotel_id, name, slug, max_occupancy, base_price, amenities) VALUES
-- Grand Hyatt rooms
(1, 'Grand King Room', 'grand-king', 2, 450.00, ARRAY['King Bed', 'City View', 'WiFi', 'Minibar']),
(1, 'Twin City View', 'twin-city', 2, 420.00, ARRAY['Twin Beds', 'City View', 'WiFi', 'Minibar']),

-- Sam Hotel rooms  
(2, 'Standard Room', 'standard', 2, 120.00, ARRAY['Queen Bed', 'WiFi', 'AC', 'TV']),
(2, 'Deluxe Room', 'deluxe', 3, 150.00, ARRAY['Queen Bed', 'Sofa Bed', 'WiFi', 'AC', 'TV']),

-- Marina Court rooms
(3, 'Deluxe Sea View', 'deluxe-sea', 2, 280.00, ARRAY['King Bed', 'Sea View', 'Balcony', 'WiFi']),
(3, 'Superior Garden View', 'superior-garden', 2, 220.00, ARRAY['Queen Bed', 'Garden View', 'WiFi', 'AC']);

-- Generate availability for next 30 days
-- This uses a more complex query to generate dates and pricing
WITH date_series AS (
    SELECT generate_series(
        CURRENT_DATE,
        CURRENT_DATE + INTERVAL '29 days',
        INTERVAL '1 day'
    )::date AS date
),
room_pricing AS (
    SELECT 
        rt.id as room_type_id,
        ds.date,
        -- Vary availability: less on Sundays (day 0), more on other days
        CASE WHEN EXTRACT(DOW FROM ds.date) = 0 THEN 2 ELSE 5 END as available_rooms,
        -- Weekend pricing: 20% more on Friday/Saturday
        CASE 
            WHEN EXTRACT(DOW FROM ds.date) IN (5, 6) THEN rt.base_price * 1.2
            ELSE rt.base_price
        END as price
    FROM room_types rt
    CROSS JOIN date_series ds
)
INSERT INTO availability (room_type_id, date, available_rooms, price)
SELECT room_type_id, date, available_rooms, price
FROM room_pricing
ORDER BY room_type_id, date;

-- Insert sample guest
INSERT INTO guests (phone, name, email, nationality) VALUES
('+60123456789', 'Ahmad Rahman', 'ahmad.rahman@email.com', 'Malaysian'),
('+60198765432', 'Sarah Lim', 'sarah.lim@email.com', 'Malaysian'),
('+60175353792', 'Test User', 'test@example.com', 'Malaysian');

-- Insert sample booking
INSERT INTO bookings (reference, guest_id, hotel_id, room_type_id, check_in_date, check_out_date, nights, total_amount, status) VALUES
('+60123456789;marinacourt;checkin15062025;checkout16062025+deluxesea+withbreakfast+booking1', 
 1, 3, 5, '2025-06-15', '2025-06-16', 1, 280.00, 'confirmed');

-- Verification queries
SELECT 'Sample Data Inserted Successfully!' as message;

SELECT 
    'Hotels: ' || COUNT(*) as summary
FROM hotels
UNION ALL
SELECT 
    'Room Types: ' || COUNT(*) as summary  
FROM room_types
UNION ALL
SELECT 
    'Availability Records: ' || COUNT(*) as summary
FROM availability
UNION ALL
SELECT 
    'Guests: ' || COUNT(*) as summary
FROM guests
UNION ALL
SELECT 
    'Bookings: ' || COUNT(*) as summary
FROM bookings;

-- Show hotels with room counts
SELECT 
    h.name as hotel_name,
    h.city,
    h.star_rating || '⭐' as rating,
    COUNT(rt.id) as room_types,
    MIN(rt.base_price) || ' - ' || MAX(rt.base_price) || ' MYR' as price_range
FROM hotels h
LEFT JOIN room_types rt ON h.id = rt.hotel_id
GROUP BY h.id, h.name, h.city, h.star_rating
ORDER BY h.name; 