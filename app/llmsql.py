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
    
    def __init__(self, db_url: str = "postgresql://sshapdaemon:noPassword1@sshapdaemon.postgres.database.azure.com:5432/postgres"):
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
        
        # Check for hotel location queries like "What are the hotels in Mumbai?"
        hotel_location_patterns = [
            r'what\s+(?:are|is)\s+the\s+hotels?\s+in\s+([a-zA-Z\s]+)',
            r'show\s+(?:me\s+)?hotels?\s+in\s+([a-zA-Z\s]+)',
            r'find\s+hotels?\s+in\s+([a-zA-Z\s]+)',
            r'list\s+hotels?\s+in\s+([a-zA-Z\s]+)',
            r'what\s+(?:are|is)\s+the\s+names?\s+of\s+(?:the\s+)?hotels?\s+in\s+([a-zA-Z\s]+)',
            r'what\s+hotels?\s+(?:are|is)\s+(?:there\s+)?in\s+([a-zA-Z\s]+)'
        ]
        
        # Check for room queries with location
        room_location_patterns = [
            r'what\s+(?:are|is)\s+the\s+(?:types\s+of\s+)?rooms?\s+(?:available\s+)?(?:in|at)\s+(?:the\s+)?hotels?\s+in\s+([a-zA-Z\s]+)',
            r'show\s+(?:me\s+)?(?:the\s+)?rooms?\s+(?:available\s+)?(?:in|at)\s+(?:the\s+)?hotels?\s+in\s+([a-zA-Z\s]+)',
            r'what\s+types\s+of\s+rooms?\s+(?:are|is)\s+(?:available\s+)?(?:in|at)\s+(?:the\s+)?hotels?\s+in\s+([a-zA-Z\s]+)'
        ]
        
        # Check for itinerary queries
        itinerary_patterns = [
            r'what\s+(?:are|is)\s+the\s+itineraries?\s+named\s+([a-zA-Z\s\d]+)',
            r'show\s+(?:me\s+)?itineraries?\s+named\s+([a-zA-Z\s\d]+)',
            r'find\s+itineraries?\s+named\s+([a-zA-Z\s\d]+)',
            r'list\s+itineraries?\s+named\s+([a-zA-Z\s\d]+)',
            r'what\s+(?:are|is)\s+the\s+details?\s+of\s+itineraries?\s+named\s+([a-zA-Z\s\d]+)',
            r'(?:what|how many)\s+(?:is|are)\s+the\s+number\s+of\s+persons\s+in\s+itinerary\s+(?:for|named)\s+([a-zA-Z\s\d]+)',
            r'number\s+of\s+persons\s+in\s+itinerary\s+(?:for|named)\s+([a-zA-Z\s\d]+)'
        ]
        
        # Look for hotel location patterns
        location = None
        for pattern in hotel_location_patterns:
            match = re.search(pattern, query.lower())
            if match:
                location = match.group(1).strip()
                # Use specialized handler for hotel location queries
                return self._handle_hotel_location_query(location)
                
        # Check for room queries with location
        for pattern in room_location_patterns:
            match = re.search(pattern, query.lower())
            if match:
                location = match.group(1).strip()
                # Use specialized handler for room queries
                return self._handle_room_location_query(location)
        
        # Check for itinerary queries
        for pattern in itinerary_patterns:
            match = re.search(pattern, query.lower())
            if match:
                itinerary_name = match.group(1).strip()
                # Use specialized handler for itinerary queries
                return self._handle_itinerary_query(itinerary_name)
        
        # For more complex queries, use the query planner
        response_list = self.sql_query_planner.run(query)
        print(response_list)
        
        # Process each decomposed query
        sql_query_list = []
        for elem in response_list:
            res = self.agent.run(elem)
            # Add token metrics tracking
            input_tokens = res.metrics['input_tokens'][0]
            output_tokens = res.metrics['output_tokens'][0]
            total_tokens = res.metrics['total_tokens'][0]
            print(f"Agent metrics - Input tokens: {input_tokens}, Output tokens: {output_tokens}, Total: {total_tokens}")
            
            sql_query_list.append(res.content)
        
        print("Raw response:")
        
        # Extract SQL queries
        sql_queries = []
        for sql_query in sql_query_list:
            query = self.extract_sql_query(sql_query)
            if query:
                sql_queries.append(query)

        all_results = []
        if sql_queries:
            # Execute the extracted SQL queries
            print("\nExecuting queries...")
            for i, sql_query in enumerate(sql_queries):
                print(f"Executing query {i+1}: {sql_query}")
                result = self.execute_query(sql_query)
                print(f"Query {i+1} results:")
                print(result)
                all_results.extend(result)
        
        # Return combined results, or empty list if none
        return all_results if all_results else []

    def final_response(self, query: str) -> str:
        """Generate a final human-readable response from SQL query results."""
        response_data = self.process_query(query)
        
        # If no results found, provide a clear message
        if not response_data:
            return "I couldn't find any information matching your query in the database."
        
        # Check for itinerary number of persons query patterns
        itinerary_persons_pattern = r'(?:what|how many)\s+(?:is|are)\s+the\s+number\s+of\s+persons\s+in\s+itinerary\s+(?:for|named)\s+([a-zA-Z\s\d]+)'
        alt_pattern = r'number\s+of\s+persons\s+in\s+itinerary\s+(?:for|named)\s+([a-zA-Z\s\d]+)'
        
        itinerary_match = re.search(itinerary_persons_pattern, query.lower()) or re.search(alt_pattern, query.lower())
        
        if itinerary_match:
            itinerary_name = itinerary_match.group(1).strip()
            
            # Format the response specifically for number of persons in itinerary
            for item in response_data:
                if 'name' in item and 'numberOfPersons' in item and 'customer_name' in item:
                    return f"The itinerary '{item['name']}' has {item['numberOfPersons']} person(s). This itinerary belongs to {item['customer_name']}."
            
            # If we couldn't find exactly what we needed in the results
            return f"I found an itinerary matching '{itinerary_name}', but couldn't determine the number of persons."
        
        # For other types of queries, use the refactoring agent
        sql_results = ""
        for item in response_data:
            # Append each dictionary as a string to the results
            sql_results += str(item) + "\n"
            
        prompt_template = f"""
        You are a SQL query refactoring agent.
        Your task is to give human readable responses from SQL queries.
        Your response should be a human readable response and not the SQL query.
        
        USER QUERY: "{query}"
        SQL RESULTS: {sql_results}
        
        Guidelines for your response:
        1. Convert the technical SQL results into a friendly, conversational response
        2. Format the information in a clear, easy-to-read way
        3. If the results include IDs or technical details, translate them into useful information
        4. Be concise but comprehensive - include all relevant information
        5. Use proper formatting with appropriate spacing
        6. Do not mention SQL or database technical details in your response
        
        Your final response should read naturally, as if a helpful assistant is answering the user's question.
        """
        
        refactored_response = refactor.run(prompt_template)
        # Add token metrics tracking
        input_tokens = refactored_response.metrics['input_tokens'][0]
        output_tokens = refactored_response.metrics['output_tokens'][0]
        total_tokens = refactored_response.metrics['total_tokens'][0]
        print(f"Refactor agent metrics - Input tokens: {input_tokens}, Output tokens: {output_tokens}, Total: {total_tokens}")
        
        return refactored_response.content

    def _handle_room_location_query(self, location: str) -> List[Dict[str, Any]]:
        """Handle room queries for hotels in a specific location."""
        print(f"Handling specialized room query for location: {location}")
        
        # Direct query to get room types in hotels in the specified location
        room_query = f"""
        SELECT 
            h.id as hotelid, 
            u.name as hotel_name, 
            r.type, 
            r."roomCapacity", 
            r."totalNumber", 
            r."basePrice"
        FROM hotels h
        JOIN users u ON h."userId" = u.id
        JOIN rooms r ON h.id = r."hotelId"
        WHERE LOWER(h.city) LIKE LOWER('%{location}%') AND u."userType" = 'hotel'
        """
        
        print(f"Executing room query: {room_query}")
        results = self.execute_query(room_query)
        
        print(f"Found {len(results)} room records for hotels in {location}")
        return results
        
    def _handle_hotel_location_query(self, location: str) -> List[Dict[str, Any]]:
        """Handle hotel location queries."""
        print(f"Handling specialized hotel location query for: {location}")
        
        # Improved direct query that joins hotels with users to get proper hotel information
        # Specifically selects hotel name from users table
        hotel_query = f"""
        SELECT 
            h.id, 
            u.name as hotel_name, 
            h.city, 
            h.rating, 
            h.description, 
            u.address
        FROM hotels h
        JOIN users u ON h."userId" = u.id
        WHERE LOWER(h.city) LIKE LOWER('%{location}%') AND u."userType" = 'hotel'
        """
        
        print(f"Executing hotel location query: {hotel_query}")
        results = self.execute_query(hotel_query)
        
        print(f"Found {len(results)} hotels in {location}")
        return results

    def _handle_itinerary_query(self, itinerary_name: str) -> List[Dict[str, Any]]:
        """Handle queries about specific itineraries."""
        print(f"Handling itinerary query for: {itinerary_name}")
        
        # Direct query to get itinerary information including number of persons
        itinerary_query = f"""
        SELECT i.id, i.name, i."numberOfPersons", i."createdAt", c.id as customer_id, u.name as customer_name
        FROM itineraries i
        JOIN customers c ON i."customerId" = c.id
        JOIN users u ON c."userId" = u.id
        WHERE LOWER(i.name) LIKE LOWER('%{itinerary_name}%')
        """
        
        print(f"Executing itinerary query: {itinerary_query}")
        results = self.execute_query(itinerary_query)
        
        print(f"Found {len(results)} itineraries matching '{itinerary_name}'")
        return results

# Main execution block
if __name__ == "__main__":
    print("Using the agent to query the database...")
    
    # Create processor instance
    processor = SQLDatabaseQueryProcessor()
    
    # Process a test query
    query = "Show me all the hotels in mumbai?"

    response = processor.final_response(query)
    print("Final response:")
    print(response)
