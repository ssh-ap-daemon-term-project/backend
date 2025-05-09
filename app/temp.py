from agno.agent import Agent
from agno.tools.sql import SQLTools
from agno.models.google import Gemini
import psycopg2
from query_refiner import SQLQueryPlannerAgent
from psycopg2.extras import RealDictCursor
import re

from dotenv import load_dotenv

load_dotenv()


db_url = "postgresql://postgres:sagnibha123#@localhost:5432/postgres"

sql_query_planner = SQLQueryPlannerAgent()

# Create an agent with Gemini model and SQL tools
agent = Agent(
    model=Gemini("gemini-2.0-flash-exp"),  # Using Gemini 2.0 Flash
    tools=[SQLTools(db_url=db_url)],
    description="""
        You are a database-driven assistant with access to a PostgreSQL database.
                Your responses should be strictly based on the available data.
                when the query comes you need to think which possible columns may have the data and then you need to query the database.
                and when querying be casreful like for example the query is "what are the hotels in kolkata" then you need to query the database like this:
                SELECT * FROM hotels WHERE city = 'kolkata'.
                and kolkata can be in any case like "Kolkata", "KOLKATA", "kolkata" etc. so you need to be case insensitive.
                (SEE YOU NEED TO HANDLE COMPLEX QUERIES EFFICIENTLY LIKE MAKING A JOIN BETWEEN TABLES AND GETTING THE DATA) 
                
                Here's the database schema you have access to:
                - users: id, username, email, hashedPassword, phone, name, address, userType (customer, hotel, driver, admin), createdAt, updatedAt
                - customers: id, userId, dob, gender, createdAt
                - hotels: id, userId, city, latitude, longitude, rating, createdAt
                - rooms: id, type, roomCapacity, totalNumber, availableNumber, bookedNumber, price, hotelId
                - roomBookings: id, customerId, roomId, startDate, endDate, numberOfPersons, createdAt
                - drivers: id, userId, carModel, carNumber, carType, seatingCapacity, createdAt
                - rideBookings: id, customerId, driverId, itineraryId, pickupLocation, dropLocation, pickupTime, dropTime, numberOfPersons, price, status, createdAt
                - admins: id, userId, createdAt
                - itineraries: id, customerId, name, numberOfPersons, createdAt
                - schedule_items: id, itinerary_id, startTime, endTime, location, description, createdAt
                - room_items: id, itinerary_id, roomId, startDate, endDate, createdAt
                - hotel_reviews: id, customerId, hotelId, rating, description, createdAt
                also see that in the user table i have gven a field name that i also the name of the customer or the hotel or the driver or the admin so you need to be careful when querying the database.
                
                Important relationships:
                - Hotel information (including latitude and longitude) is stored in the "hotels" table
                - Room information is stored in the "rooms" table, linked to hotels through hotelId
                - Customer information is in the "customers" table, linked to users through userId
                - Reviews for hotels are in the "hotel_reviews" table
                - DONOT MAKE THE THING CASE SESNSITIVE, DO NOT USE THE TABLE NAME IN THE QUERY, JUST USE THE COLUMNS
                - The "roomBookings" table contains booking information for rooms, linked to customers through customerId
                - The "rideBookings" table contains booking information for rides, linked to customers through customerId and drivers through driverId
                
                When processing queries, be case-insensitive and understand different ways people might refer to tables or columns.
                For example, if someone asks about "hotel location", "hotel coordinates", "lat/long of hotels", they're referring to the latitude and longitude columns in the hotels table.
                
                Always perform queries using proper SQL syntax with quotes around string values and correct joins between tables as needed.
                
                VERY IMPORTANT: I need you to output your final SQL query in a code block like this:
                ```sql
                SELECT * FROM hotels WHERE LOWER(city) LIKE LOWER('%kolkata%');
                ```
                Make sure the query is exactly what should be executed, with correct table and column names.
                DONOT GIVE THE RESPONSE AS SQL QUERY SO GIVE A RESPONSE AFTER EXECUTING THE QUERY IN THE DATABASE
    """
)

# Function to extract SQL query from the response
def extract_sql_query(response_text):
    # Pattern to match SQL code blocks
    pattern = r"```sql\s*(.*?)\s*```"
    match = re.search(pattern, response_text, re.DOTALL)
    if match:
        query = match.group(1).strip()
        # Fix camelCase columns by adding quotes
        query = re.sub(r'(\w+)\.(\w*[A-Z]\w*)', r'\1."\2"', query)
        return query
    
    # Try to find raw SQL if not in a code block
    sql_pattern = r"SELECT.*?;?"
    sql_match = re.search(sql_pattern, response_text, re.DOTALL | re.IGNORECASE)
    if sql_match:
        query = sql_match.group(0).strip()
        # Fix camelCase columns by adding quotes
        query = re.sub(r'(\w+)\.(\w*[A-Z]\w*)', r'\1."\2"', query)
        return query
    
    return None
# Function to execute a query against the database
def execute_query(query):
    try:
        # Connect to the database
        connection = psycopg2.connect(db_url)
        
        # Create a cursor with dictionary-like results
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            # Execute the query
            cursor.execute(query)
            
            # Check if there are results to fetch
            if cursor.description:
                # Fetch all results and convert to a list of dictionaries
                results = cursor.fetchall()
                return [dict(row) for row in results]
            return []
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        return []
    finally:
        # Make sure the connection is closed
        if connection:
            connection.close()

# Test with the agent
print("Using the agent to query the database...")

def processquery(query):
    # response = agent.run("how many hotels are there in mumbai and what are their latitude and longitude?")
    response_list = sql_query_planner.run(query)
    print(response_list)
    sql_query_list = []
    for elem in response_list:
        res = agent.run(elem)
        sql_query_list.append(res.content)
    # response_content = response.content
    print("Raw response:")
    # print(response_content)

    # Extract the SQL query
    sql_queries = []
    for sql_query in sql_query_list:
        query = extract_sql_query(sql_query)
        if query :
            sql_queries.append(query)

    if sql_queries:
        # Execute the extracted SQL queries
        print("\nExecuting queries...")
        for sql_query in sql_queries:
            result = execute_query(sql_query)
            print("Query results:")
            print(result)

    return result

if __name__=="__main__":
    
    response = processquery("how many hotels are there in mumbai and what are their latitude and longitude?")
    print(response)