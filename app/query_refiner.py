import ast
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google import Gemini
from agno.models.groq import Groq
import re

def _unwrap_metric(x):
    """
    Helper to turn either an int or a single‐element list into an int.
    """
    if isinstance(x, list) and len(x) > 0:
        return x[0]
    return x if isinstance(x, int) else None

class SQLQueryPlannerAgent:
    def __init__(self):
        """
        Initializes the SQLQueryPlannerAgent with the Gemini model and detailed planner configuration.
        """
        load_dotenv()

        self.agent = Agent(
            model=Gemini(id="gemini-2.0-flash"),
            description=self._build_description(),
            show_tool_calls=True,
            markdown=True
        )

    def _build_description(self):
        """
        Constructs the description prompt used to guide the query planner.
        """
        return """
        You are an intelligent SQL query planner for a travel assistant that uses a PostgreSQL database. Your task is to read any user query and extract a list of structured sub-query tasks — each describing what information needs to be retrieved from the database, from which table and columns, and how the data is related. 

        Rules:
        - Only include sub-query tasks that are answerable from the database schema below.
        - Be case-insensitive in textual matches (e.g., city names).
        - Understand relationships (e.g., hotelId links hotels and rooms; userId links users and customers/hotels/drivers/admins).
        - Join tables when necessary to get descriptive information like names or prices.
        - Do NOT generate SQL queries here. Output should be a Python list of specific data retrieval tasks in plain English.
        - DO NOT include tasks involving external knowledge or generic advice. Focus strictly on what is retrievable from the schema.

        Database Schema:
        - users: id, username, email, hashedPassword, phone, name, address, userType (customer, hotel, driver, admin), createdAt, updatedAt
        - customers: id, userId, dob, gender, createdAt
        - hotels: id, userId, city, latitude, longitude, rating, description, createdAt
        - rooms: id, type (basic, luxury, suite, deluxe), roomCapacity, totalNumber, basePrice, hotelId, createdAt
        - roomBookings: id, customerId, roomId, startDate, endDate, numberOfPersons, createdAt
        - drivers: id, userId, carModel, carNumber, carType (sedan, suv, hatchback, luxury), seatingCapacity, createdAt
        - rideBookings: id, customerId, driverId, itineraryId, pickupLocation, dropLocation, pickupTime, dropTime, numberOfPersons, price, status (pending, confirmed, completed, cancelled), createdAt
        - admins: id, userId, createdAt
        - itineraries: id, customerId, name, numberOfPersons, createdAt
        - schedule_items: id, itineraryId, startTime, endTime, location, description, createdAt
        - room_items: id, itineraryId, roomId, startDate, endDate, createdAt
        - hotel_reviews: id, customerId, hotelId, rating, description, createdAt
        
        Instructions:
        - **** If any location information is needed, include latitude and longitude from the hotels table.****
        - **** If hotel information is needed, include latitude and longitude from the hotels table.****
        - If room information is needed, include type, roomCapacity, totalNumber, and basePrice from the rooms table.
        
        Important relationships:
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

        Example:
        User Query: "Tell me about tourist locations in Mumbai and give a 7 days plan for hotels and other side activities, my budget is moderate"
        
        --- Important instruction : Do not give python or json these kind of words in the output.

        Output:
        [
        "Get all hotels where LOWER(city) LIKE LOWER('%Mumbai%')",
        "Join with users on userId to retrieve hotel names",
        "Retrieve rooms for each hotel including type, roomCapacity, totalNumber, and basePrice",
        "Filter rooms with basePrice in the moderate range (e.g., 1000-3000)",
        "Get reviews for each hotel by joining on hotelId with hotel_reviews",
        ]
        
    Example:
        User Query: "Find locations near the Taj Hotel in Mumbai."
        
        --- Important instruction : Do not give python or json these kind of words in the output.

        Output:
        [
        "Get all hotels where LOWER(city) LIKE LOWER('%Mumbai%')",
        "Join with users on userId to retrieve hotel names",
        "Get latitude and longitude of the hotel",
        ]
        """
    def run(self, user_query: str) -> list:
        """
        Executes the agent on the user query and returns the list of sub-query tasks.

        :param user_query: A natural language user input describing travel requirements.
        :return: A Python list of structured sub-query tasks.
        """
        response = self.agent.run(user_query)
        response_content = response.content
        
        # Add token metrics tracking
        input_tokens = _unwrap_metric(response.metrics.get('input_tokens'))
        output_tokens = _unwrap_metric(response.metrics.get('output_tokens'))
        total_tokens = _unwrap_metric(response.metrics.get('total_tokens'))
        print(f"Query planner metrics - Input tokens: {input_tokens}, Output tokens: {output_tokens}, Total: {total_tokens}")
        
        cleaned = self._clean_response(response_content)
        return self._parse_to_list(cleaned)

    def _clean_response(self, response: str) -> str:
        """
        Removes markdown formatting and extraneous syntax from the agent's response.

        :param response: Raw response from the agent.
        :return: Cleaned string.
        """
        return response.replace("```python", "").replace("```", "").strip()

    def _parse_to_list(self, cleaned: str) -> list:
        """
        Safely parses the cleaned string into a Python list.

        :param cleaned: String that should represent a Python list.
        :return: Parsed Python list.
        """
        try:
            # Try standard literal_eval first
            if cleaned.startswith("[") and cleaned.endswith("]"):
                try:
                    return ast.literal_eval(cleaned)
                except (SyntaxError, ValueError):
                    # Continue to alternative parsing if literal_eval fails
                    pass
            
            # If not a valid Python list, try to extract items manually
            # Look for patterns like "1. Item" or "- Item" and extract the items
            items = []
            
            # Try to match numbered items (1. Item, 2. Item, etc.)
            numbered_pattern = r'(?:^|\n)\s*(\d+)[.)] (.*?)(?=\n\s*\d+[.)]|\Z)'
            matches = re.findall(numbered_pattern, cleaned, re.DOTALL)
            if matches:
                for _, item in matches:
                    items.append(item.strip())
                return items
            
            # Try to match bullet points (- Item, • Item, etc.)
            bullet_pattern = r'(?:^|\n)\s*[-•*] (.*?)(?=\n\s*[-•*]|\Z)'
            matches = re.findall(bullet_pattern, cleaned, re.DOTALL)
            if matches:
                for item in matches:
                    items.append(item.strip())
                return items
                
            # If we get here and still have text, try to split by newlines
            if cleaned and not items:
                # Filter out empty lines and common prefixes
                lines = [line.strip() for line in cleaned.split('\n') 
                        if line.strip() and not line.strip().lower().startswith(('python', 'json', 'list', 'output'))]
                if lines:
                    return lines
            
            # If nothing worked and we have a non-empty string that doesn't look like a list
            if cleaned and not cleaned.startswith("["):
                # Last resort: treat the whole string as a single query
                return [cleaned]
                
            # If all else fails, return an empty list
            return []
        except Exception as e:
            print(f"Error parsing list: {e}")
            print(f"Original text: {cleaned}")
            # Default to treating the whole string as a single query item
            if cleaned:
                return [cleaned]
            return []
if __name__ == "__main__":
    planner = SQLQueryPlannerAgent()
    user_input = "Tell me about tourist locations in Bangalore and give a 7 days plan for hotels and other side activities, my budget is moderate, so recommend hotels accordingly."
    
    try:
        query_tasks = planner.run(user_input)
        print("Sub-query Tasks:")
        for task in query_tasks:
            print("-", task)
    except Exception as e:
        print(f"Error: {e}")