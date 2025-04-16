import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

# SQL queries with proper parameterization and quoted column names
sql_queries = [
    # 1. Get all hotels in a specific city
    """
    SELECT u.id, u.name, h.city, h.latitude, h.longitude, h.rating
    FROM users u
    JOIN hotels h ON u.id = h."userId"
    WHERE LOWER(h.city) = LOWER(%s);
    """,

    # 2. Get hotel details by hotel name (partial match)
    """
    SELECT u.id, u.name, h.city, h.latitude, h.longitude, h.rating
    FROM users u
    JOIN hotels h ON u.id = h."userId"
    WHERE LOWER(u.name) LIKE LOWER(CONCAT('%%', %s, '%%'));
    """,

    # 3. Get hotel coordinates by hotel name
    """
    SELECT h.latitude, h.longitude
    FROM users u
    JOIN hotels h ON u.id = h."userId"
    WHERE LOWER(u.name) LIKE LOWER(CONCAT('%%', %s, '%%'));
    """,

    # 4. Get all hotels near a specified hotel (same city)
    """
    SELECT u.name, h.city, h.rating, h.description
    FROM hotels h
    JOIN users u ON h."userId" = u.id
    WHERE LOWER(h.city) = (
        SELECT LOWER(h1.city)
        FROM hotels h1
        JOIN users u1 ON h1."userId" = u1.id
        WHERE LOWER(u1.name) LIKE LOWER(CONCAT('%%', %s, '%%'))
        LIMIT 1
    );
    """,
    
    """
    SELECT 
    u.name AS hotel_name,
    h.city AS city,
    h.rating AS hotel_rating,
    r.type AS room_type,
    r."roomCapacity" AS capacity,
    r.* -- This will show all columns from the rooms table
FROM 
    hotels h
JOIN 
    users u ON h."userId" = u.id
JOIN 
    rooms r ON h.id = r."hotelId"
WHERE 
    LOWER(h.city) = LOWER(%s)
LIMIT 1;
    """,
    

    # 5. Get hotels in a given city with their average rating
    """
    SELECT u.name AS hotel_name, h.rating, h.description
    FROM hotels h
    JOIN users u ON h."userId" = u.id
    WHERE LOWER(h.city) = LOWER(%s);
    """
]