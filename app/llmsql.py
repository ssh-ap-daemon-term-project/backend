from agno.agent import Agent
from agno.tools.sql import SQLTools
from agno.models.google import Gemini
import psycopg2
# Conditional import based on how the file is being used
try:
    # Try package-style import first (for when used in FastAPI)
    from .query_refiner import SQLQueryPlannerAgent
except ImportError:
    # Fall back to direct import (for when run as a script)
    from query_refiner import SQLQueryPlannerAgent
from psycopg2.extras import RealDictCursor
import re
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv

load_dotenv()

refactor = Agent(
    model=Gemini("gemini-2.0-flash-exp"),
    instructions="""
    You are a SQL query refactoring agent.
    Your task is to give human readable responses from SQL queries.
    You should only give the human readable response and not the SQL query.
    """
)



class SQLDatabaseQueryProcessor:
    """A class to process natural language queries to SQL and execute them against a database."""
    
    def __init__(self, db_url: str = "postgresql://postgres:sagnibha123#@localhost:5432/postgres"):
        """Initialize with database connection and LLM agents."""
        self.db_url = db_url
        self.sql_query_planner = SQLQueryPlannerAgent()
        self.agent = Agent(
            model=Gemini("gemini-2.0-flash-exp"),  
            tools=[SQLTools(db_url=self.db_url)],
            description="""
    You are a database-driven assistant with access to a PostgreSQL database.
    Your responses should be strictly based on the available data.
    When a query comes, think about which columns may have the data and formulate an appropriate database query.
    
    Be careful with your queries. For example, if the query is "what are the hotels in kolkata", use:
    SELECT * FROM hotels WHERE LOWER(city) LIKE LOWER('%kolkata%');
    
    Always use case-insensitive matching for text fields and handle complex queries by creating proper JOINs between tables.
    If only hotel names are requested, return only the names instead of all table fields.
    
    Here's the complete database schema:
    
    - users: id, username, email, hashedPassword, phone, name, address, userType (customer, hotel, driver, admin), createdAt, updatedAt
    
    - customers: id, userId, dob, gender, createdAt
      * Relationships: user (User), bookings (RoomBooking), rideBookings (RideBooking), itineraries (Itinerary), reviews (HotelReview)
    
    - hotels: id, userId, city, latitude, longitude, rating, description, createdAt
      * Relationships: user (User), rooms (Room), reviews (HotelReview)
    
    - rooms: id, type (basic, luxury, suite, deluxe), roomCapacity, totalNumber, basePrice, hotelId, createdAt
      * Relationships: hotel (Hotel), bookings (RoomBooking), roomItems (RoomItem)
    
    - roomBookings: id, customerId, roomId, startDate, endDate, numberOfPersons, createdAt
      * Relationships: customer (Customer), room (Room)
    
    - drivers: id, userId, carModel, carNumber, carType (sedan, suv, hatchback, luxury), seatingCapacity, createdAt
      * Relationships: user (User), rideBookings (RideBooking)
    
    - rideBookings: id, customerId, driverId, itineraryId, pickupLocation, dropLocation, pickupTime, dropTime, numberOfPersons, price, status (pending, confirmed, completed, cancelled), createdAt
      * Relationships: customer (Customer), driver (Driver), itinerary (Itinerary)
    
    - admins: id, userId, createdAt
      * Relationships: user (User)
    
    - itineraries: id, customerId, name, numberOfPersons, createdAt
      * Relationships: customer (Customer), scheduleItems (ScheduleItem), roomItems (RoomItem), rideBookings (RideBooking)
    
    - schedule_items: id, itineraryId, startTime, endTime, location, description, createdAt
      * Relationships: itinerary (Itinerary)
    
    - room_items: id, itineraryId, roomId, startDate, endDate, createdAt
      * Relationships: itinerary (Itinerary), room (Room)
    
    - hotel_reviews: id, customerId, hotelId, rating, description, createdAt
      * Relationships: customer (Customer), hotel (Hotel)
    
    Important relationships and tips:
    
    1. User information:
       - The 'users' table contains core user data (name, email, etc.)
       - Each user has a userType (customer, hotel, driver, admin)
       - Detailed information for each user type is in the respective tables linked via userId
    
    2. Hotel information:
       - Hotel details (name, address) are in the 'users' table where userType='hotel'
       - Additional hotel details (city, coordinates, rating) are in the 'hotels' table
       - Get hotel name by joining hotels with users on hotels.userId = users.id
    
    3. Room and booking information:
       - Room information (type, capacity, price) is in the 'rooms' table
       - Room bookings are tracked in 'roomBookings' table
       - Rooms are linked to hotels through hotelId
    
    4. Travel itineraries:
       - 'itineraries' table stores travel plans for customers
       - 'schedule_items' contains activities in an itinerary
       - 'room_items' links rooms to itineraries (hotel stays)
       - 'rideBookings' handles transportation arrangements
    
    5. Reviews:
       - Hotel reviews are stored in 'hotel_reviews' table
    
    Always use proper SQL syntax with quotes around string values and correct joins between tables.
    Make sure your queries are case-insensitive for text matching.
    
    VERY IMPORTANT: Output your final SQL query in a code block like this:
    ```sql
    SELECT * FROM hotels WHERE LOWER(city) LIKE LOWER('%kolkata%');
    ```
    
    Ensure the query is exactly what should be executed, with correct table and column names.
    After executing the query, provide a clear, concise response based on the database results.
"""
        )

    def extract_sql_query(self, response_text: str) -> Optional[str]:
        """Extract SQL query from response text."""
        pattern = r"```sql\s*(.*?)\s*```"
        match = re.search(pattern, response_text, re.DOTALL)
        if match:
            query = match.group(1).strip()
            query = self._fix_camel_case(query)
            return query
        
        # Try to find raw SQL if not in a code block
        sql_pattern = r"SELECT.*?;?"
        sql_match = re.search(sql_pattern, response_text, re.DOTALL | re.IGNORECASE)
        if sql_match:
            query = sql_match.group(0).strip()
            # Fix camelCase columns by adding quotes
            query = self._fix_camel_case(query)
            return query
        
        return None
    
    def _fix_camel_case(self, query: str) -> str:
        """Add quotes around camelCase column names."""
        return re.sub(r'(\w+)\.(\w*[A-Z]\w*)', r'\1."\2"', query)

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a SQL query against the database."""
        connection = None
        try:
            # Connect to the database
            connection = psycopg2.connect(self.db_url)
            
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

    def process_query(self, query: str) -> List[Dict[str, Any]]:
        """Process a natural language query through the SQL query planner and agent."""
        # Get decomposed queries from the query planner
        response_list = self.sql_query_planner.run(query)
        print(response_list)
        
        # Process each decomposed query
        sql_query_list = []
        for elem in response_list:
            res = self.agent.run(elem)
            sql_query_list.append(res.content)
        
        print("Raw response:")
        
        # Extract SQL queries
        sql_queries = []
        for sql_query in sql_query_list:
            query = self.extract_sql_query(sql_query)
            if query:
                sql_queries.append(query)

        results = []
        if sql_queries:
            # Execute the extracted SQL queries
            print("\nExecuting queries...")
            for sql_query in sql_queries:
                result = self.execute_query(sql_query)
                print("Query results:")
                print(result)
                results.append(result)
        
        # Return the last result for backward compatibility
        return results[-1] if results else []

    def final_response(self, query: str) -> str:
        response = self.process_query(query)
        sql_results = ""
        for item in response:
            # Append each dictionary as a string to the results
            sql_results += str(item) + "\n"
        prompt_template = f"""
        You are a SQL query refactoring agent.
        Your task is to give human readable responses from SQL queries.
        Your response should be a human readable response and not the SQL query.
        this is the user query: {query}
        this is the SQL query results: {sql_results}
        """
        refactored_response = refactor.run(prompt_template)
        return refactored_response.content

# Main execution block
if __name__ == "__main__":
    print("Using the agent to query the database...")
    
    # Create processor instance
    processor = SQLDatabaseQueryProcessor()
    
    # Process a test query
    query = "what is the latitude longitude of the hotel hyatt in delhi?"
    response = processor.final_response(query)
    print("Final response:")
    print(response)
