import os
import re
import time
import json
import requests
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google import Gemini

# Import the SQLDatabaseQueryProcessor from your existing file
from llmsql import SQLDatabaseQueryProcessor

load_dotenv()


# here i need to make two functions one that uses the query along with some prompt to get the lat long of the hotel using the llmsql.py ka functions and another a websearch agent to do websearch and suggest locations inproxitmity to that hotel

def get_lat_long_of_hotel(query: str) -> Optional[Dict[str, float]]:
    """
    Query the database to get the latitude and longitude of a hotel and extract the values.
    
    Args:
        query: Natural language query about a hotel
        
    Returns:
        Dictionary with 'latitude' and 'longitude' if found, None otherwise
    """
    # Create an instance of the SQLDatabaseQueryProcessor
    db_processor = SQLDatabaseQueryProcessor()
    
    # Modify the query to specifically ask for latitude and longitude
    hotel_query = "if the user asks for best places to visit from the hotel_name then give the latitude and longitude of the hotel name in the query. " + query
    
    # Query the database to get the latitude and longitude of the hotel
    results = db_processor.process_query(hotel_query)
    print("Database results:", results)
    
    # Check if we got results
    if not results or len(results) == 0:
        print("No results found for the hotel")
        return None
    
    # Try to extract latitude and longitude from the results
    try:
        # Check if the first result has latitude and longitude fields
        first_result = results[0]
        if 'latitude' in first_result and 'longitude' in first_result:
            return {
                'latitude': float(first_result['latitude']),
                'longitude': float(first_result['longitude'])
            }
        else:
            # Process the results using a more flexible approach
            # Create an agent to extract the coordinates from the result
            agent = Agent(
                model=Gemini(id="gemini-2.0-flash"),
                instructions="""
                You are an expert at extracting geographical coordinates from data.
                Given a set of database results about a hotel, extract the latitude and longitude.
                Return ONLY a JSON object with 'latitude' and 'longitude' as floating point numbers.
                Example output: {"latitude": 19.0760, "longitude": 72.8777}
                If coordinates cannot be found, return {"latitude": null, "longitude": null}
                """
            )
            
            # Convert results to a string and pass to the agent
            result_str = json.dumps(results, default=str)
            response = agent.run(f"Extract latitude and longitude from these results: {result_str}")
            
            # Parse the response as JSON
            coordinates = json.loads(response.content)
            
            # Validate the parsed coordinates
            if coordinates and 'latitude' in coordinates and 'longitude' in coordinates:
                if coordinates['latitude'] is not None and coordinates['longitude'] is not None:
                    return {
                        'latitude': float(coordinates['latitude']),
                        'longitude': float(coordinates['longitude'])
                    }
            
            print("Could not extract coordinates from results")
            return None
            
    except Exception as e:
        print(f"Error extracting coordinates: {str(e)}")
        return None    
    
    
    

def websearch_agent(coordinates: Dict[str, float], hotel_name: str = "", days: int = 3) -> List[Dict[str, Any]]:
    """
    Find locations in proximity to given coordinates and create a detailed itinerary.
    
    Args:
        coordinates: Dictionary with 'latitude' and 'longitude' values
        hotel_name: Optional name of the hotel for context
        days: Number of days for the itinerary (default: 3)
        
    Returns:
        List of daily itinerary plans with activities and recommendations
    """
    # Extract number of days from the query if provided
    
    # Create an instance of the Agent for web search and itinerary planning
    agent = Agent(
        model=Gemini(id="gemini-2.0-flash"),
        instructions="""
        You are a professional travel itinerary planner. When given coordinates and a hotel name, 
        create a comprehensive day-by-day travel plan for a tourist.

        For each day in the itinerary:
        1. Recommend 2-4 nearby attractions or activities with brief descriptions
        2. Suggest breakfast, lunch, and dinner options (include local specialties when possible)
        3. Include approximate travel times between locations
        4. Add helpful tips specific to each location (best time to visit, what to wear, etc.)
        
        Structure your response as a valid JSON array of day objects with this format:
        [
          {
            "day": 1,
            "title": "Day 1: Exploring Historical Sites",
            "activities": [
              {
                "time": "9:00 AM - 11:30 AM",
                "name": "Activity Name",
                "description": "Brief description of the activity",
                "tips": "Helpful tips for visitors"
              },
              {...more activities...}
            ],
            "meals": {
              "breakfast": "Breakfast recommendation",
              "lunch": "Lunch recommendation",
              "dinner": "Dinner recommendation"
            },
            "travel_tips": "Overall tips for the day"
          },
          {...more days...}
        ]
        
        Ensure each recommendation is specific, realistic, and appropriate for the actual location.
        Research the area around the coordinates to find genuine attractions and restaurants.
        
        IMPORTANT: Your entire response must be valid JSON - nothing else. No introduction or conclusion text.
        """
    )

    # Create the query with the coordinates and days
    search_query = f"Create a {days}-day travel itinerary for a tourist staying at coordinates {coordinates['latitude']}, {coordinates['longitude']}"
    if hotel_name:
        search_query += f" (at {hotel_name})"
    
    # Run the agent with the query
    response = agent.run(search_query)
    
    try:
        # Parse the response to extract the itinerary
        itinerary = json.loads(response.content)
        return itinerary
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Response content preview: {response.content[:200]}...")
        
        # Try to extract JSON from the text response
        json_pattern = r'\[\s*\{.*\}\s*\]'
        match = re.search(json_pattern, response.content, re.DOTALL)
        if match:
            try:
                itinerary = json.loads(match.group(0))
                return itinerary
            except json.JSONDecodeError:
                pass
                
        # Fallback: Use LLM to fix the JSON
        try:
            fix_agent = Agent(
                model=Gemini(id="gemini-2.0-flash"),
                instructions="""
                You are a JSON formatting expert. Your task is to convert the given text 
                to a valid JSON array representing a travel itinerary.
                
                The output should be an array of day objects, each containing:
                - day (number)
                - title (string)
                - activities (array of activity objects)
                - meals (object with breakfast, lunch, dinner)
                - travel_tips (string)
                
                Fix any JSON syntax errors and ensure the result is properly formatted.
                Return ONLY the fixed JSON with no additional text.
                """
            )
            fixed_response = fix_agent.run(f"Fix this JSON for a travel itinerary: {response.content}")
            return json.loads(fixed_response.content)
        except Exception as fix_error:
            print(f"Failed to fix JSON: {fix_error}")
            
        # Return a basic fallback itinerary if all else fails
        return [
            {
                "day": 1,
                "title": "Day 1: Exploring the Area",
                "activities": [
                    {
                        "time": "10:00 AM - 12:00 PM",
                        "name": "Local Sightseeing",
                        "description": "Explore the area around your hotel",
                        "tips": "Ask the hotel concierge for recommendations"
                    }
                ],
                "meals": {
                    "breakfast": "Hotel breakfast",
                    "lunch": "Try a local restaurant",
                    "dinner": "Hotel restaurant or nearby dining"
                },
                "travel_tips": "Local transportation options may be available at your hotel"
            }
        ]    
    
    
if __name__ == "__main__":
    # Example query
    query = "where can i visit from The Oberoi Amarvilas for 3 days"
    
    # Extract hotel name from query
    hotel_name_match = re.search(r'near the (.*?)(?:in|\.| for)', query)
    hotel_name = hotel_name_match.group(1).strip() if hotel_name_match else ""
    
    # Extract number of days if mentioned
    days_match = re.search(r'for (\d+) days?', query)
    days = int(days_match.group(1)) if days_match else 3  # Default to 3 days
    
    # Get latitude and longitude of the hotely
    lat_long = get_lat_long_of_hotel(query)
    print(f"Latitude and Longitude of the hotel: {lat_long}")
    
    # Get itinerary using web search with the coordinates
    if lat_long:
        itinerary = websearch_agent(lat_long, hotel_name, days)
        print(f"Created {len(itinerary)} day itinerary:")
        for day_plan in itinerary:
            print(f"\n{day_plan['title']}")
            for activity in day_plan['activities']:
                print(f"  • {activity['time']}: {activity['name']}")
            print(f"  Meals: Breakfast at {day_plan['meals']['breakfast']}, Dinner at {day_plan['meals']['dinner']}")
    else:
        print("Could not find hotel coordinates to create an itinerary")