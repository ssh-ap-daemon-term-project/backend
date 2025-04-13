import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google import Gemini

# Import the SQLDatabaseQueryProcessor from your existing file
try:
    from .llmsql import SQLDatabaseQueryProcessor
except ImportError:
    from llmsql import SQLDatabaseQueryProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class TravelPlanner:
    def __init__(self):
        self.db_processor = SQLDatabaseQueryProcessor()
        self.gemini_model_id = "gemini-2.0-flash"

    def extract_query_parameters(self, query: str) -> Dict[str, Any]:
        """
        Extract key parameters from a natural language query: location, days, budget, hotel name.
        
        Args:
            query: Natural language query about travel plans
            
        Returns:
            Dictionary with extracted parameters
        """
        # Create a parameters agent to extract structured information
        parameters_agent = Agent(
            model=Gemini(id=self.gemini_model_id),
            instructions="""
            Extract key travel planning parameters from the user's query.
            Return a JSON object with these fields:
            - location: Primary location/city mentioned (empty string if none)
            - days: Number of days for the trip (integer, default 3)
            - budget: Budget in Indian Rupees (integer, null if not specified)
            - hotel_name: Name of specific hotel if mentioned (empty string if none)
            - hotel_type: Type of accommodation preferred (e.g., "luxury", "budget", "moderate", empty string if none)
            - interests: List of activities/interests mentioned (empty array if none)
            
            Example output:
            {"location": "Mumbai", "days": 5, "budget": 50000, "hotel_name": "Taj Hotel", "hotel_type": "luxury", "interests": ["historical sites", "beaches"]}
            """
        )
        
        response = parameters_agent.run(f"Extract travel parameters from: {query}")
        
        try:
            parameters = json.loads(response.content)
            logger.info(f"Extracted parameters: {parameters}")
            return parameters
        except json.JSONDecodeError:
            logger.error(f"Failed to parse parameters from response: {response.content}")
            # Fallback to default parameters
            return {
                'location': '',
                'days': 3,
                'budget': None,
                'hotel_name': '',
                'hotel_type': '',
                'interests': []
            }

    def find_hotels(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find hotels based on parameters, taking into account location, budget, and hotel type.
        """
        hotels = []
        query_parts = []
        
        # Build the database query based on available parameters
        if parameters['location']:
            query_parts.append(f"in {parameters['location']}")
        
        if parameters['hotel_name']:
            query_parts.append(f"named {parameters['hotel_name']}")
        
        if parameters['hotel_type']:
            query_parts.append(f"that are {parameters['hotel_type']}")
        
        if parameters['budget']:
            # Factor in the number of days to calculate per-night budget
            days = parameters['days'] or 3
            nightly_budget = parameters['budget'] / days
            query_parts.append(f"with price less than {nightly_budget} per night")
        
        # Combine the query parts
        if query_parts:
            hotel_query = "Find hotels " + " and ".join(query_parts)
            hotel_query += " with their names, ratings, prices, latitudes, longitudes, and cities."
        else:
            hotel_query = "Find popular hotels with their names, ratings, prices, latitudes, longitudes, and cities."
        
        logger.info(f"Hotel query: {hotel_query}")
        
        # Query the database
        try:
            results = self.db_processor.process_query(hotel_query)
            logger.info(f"Found {len(results)} hotels matching criteria")
            
            # Process the results
            for hotel in results:
                if 'latitude' in hotel and 'longitude' in hotel and hotel['latitude'] and hotel['longitude']:
                    try:
                        # Create a standardized hotel entry
                        hotel_entry = {
                            'name': hotel.get('name', 'Unknown Hotel'),
                            'latitude': float(hotel['latitude']),
                            'longitude': float(hotel['longitude']),
                            'city': hotel.get('city', ''),
                            'price': float(hotel.get('basePrice', 0)) if 'basePrice' in hotel else 
                                    float(hotel.get('price', 0)),
                            'rating': float(hotel.get('rating', 0)) if 'rating' in hotel else 0
                        }
                        
                        hotels.append(hotel_entry)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to process hotel {hotel.get('name', 'Unknown')}: {e}")
            
            # If we have hotels but none with coordinates, try a more general query
            if not hotels and results:
                logger.info("Found hotels but none with valid coordinates, trying direct coordinates query")
                return self.get_hotel_coordinates(parameters)
                
            return hotels
        except Exception as e:
            logger.error(f"Error finding hotels: {e}")
            return []

    def get_hotel_coordinates(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Targeted query to get coordinates for hotels when standard query fails
        """
        query = "Get coordinates for "
        if parameters['hotel_name']:
            query += f"{parameters['hotel_name']} "
        if parameters['location']:
            query += f"in {parameters['location']} "
        
        query += "including latitude and longitude fields"
        
        try:
            results = self.db_processor.process_query(query)
            
            hotels = []
            for hotel in results:
                if 'latitude' in hotel and 'longitude' in hotel and hotel['latitude'] and hotel['longitude']:
                    try:
                        hotels.append({
                            'name': hotel.get('name', 'Unknown Hotel'),
                            'latitude': float(hotel['latitude']),
                            'longitude': float(hotel['longitude']),
                            'city': hotel.get('city', parameters['location']),
                            'price': float(hotel.get('basePrice', 0)) if 'basePrice' in hotel else 0,
                            'rating': float(hotel.get('rating', 0)) if 'rating' in hotel else 0
                        })
                    except (ValueError, TypeError):
                        continue
            
            return hotels
        except Exception as e:
            logger.error(f"Error getting hotel coordinates: {e}")
            return []

    def check_hotel_budget_compatibility(self, hotels: List[Dict[str, Any]], parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filter and rank hotels based on budget compatibility
        """
        if not parameters['budget'] or not hotels:
            return hotels
            
        days = parameters['days'] or 3
        compatible_hotels = []
        borderline_hotels = []
        
        for hotel in hotels:
            # Calculate total stay cost
            nightly_price = hotel.get('price', 0)
            total_cost = nightly_price * days
            
            # Add budget compatibility flag
            hotel['total_cost'] = total_cost
            hotel['within_budget'] = total_cost <= parameters['budget']
            
            # Sort into appropriate list
            if hotel['within_budget']:
                compatible_hotels.append(hotel)
            elif total_cost <= parameters['budget'] * 1.2:  # Allow 20% flexibility
                hotel['budget_note'] = "Slightly over budget"
                borderline_hotels.append(hotel)
        
        # Return compatible hotels first, then borderline options
        return compatible_hotels + borderline_hotels if compatible_hotels else borderline_hotels or hotels

    def generate_itinerary(self, hotel: Dict[str, Any], parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate a travel itinerary based on hotel location and user parameters
        """
        # Create a tailored prompt based on parameters
        interests = ', '.join(parameters['interests']) if parameters['interests'] else "popular tourist activities"
        budget_note = ""
        if parameters['budget']:
            per_day_budget = (parameters['budget'] - (hotel.get('total_cost', 0))) / parameters['days']
            if per_day_budget > 0:
                budget_note = f" with approximately {per_day_budget:.2f} INR per day for activities and meals"
            else:
                budget_note = " with a very tight budget for activities and meals"
        
        # Create the itinerary agent
        agent = Agent(
            model=Gemini(id=self.gemini_model_id),
            instructions=f"""
            You are a professional travel itinerary planner. Create a detailed {parameters['days']}-day 
            travel plan for a tourist staying at {hotel['name']} in {hotel.get('city', parameters['location'])}.
            
            Focus on {interests}{budget_note}.
            
            For each day in the itinerary:
            1. Recommend 2-4 nearby attractions or activities with descriptions
            2. Suggest breakfast, lunch, and dinner options (include local specialties)
            3. Include approximate travel times between locations
            4. Add helpful tips specific to each location
            
            Structure your response as a valid JSON array of day objects with this format:
            [
              {{
                "day": 1,
                "title": "Day 1: [Theme]",
                "activities": [
                  {{
                    "time": "9:00 AM - 11:30 AM",
                    "name": "Activity Name",
                    "description": "Brief description",
                    "tips": "Helpful tips"
                  }}
                ],
                "meals": {{
                  "breakfast": "Recommendation",
                  "lunch": "Recommendation",
                  "dinner": "Recommendation"
                }},
                "travel_tips": "Overall tips"
              }}
            ]
            
            IMPORTANT: Your entire response must be valid JSON with no other text.
            """
        )

        # Generate the itinerary
        coordinates_str = f"{hotel['latitude']}, {hotel['longitude']}"
        query = f"Create a {parameters['days']}-day travel itinerary for a tourist staying at coordinates {coordinates_str} ({hotel['name']})"
        
        try:
            response = agent.run(query)
            return self.process_itinerary_response(response.content)
        except Exception as e:
            logger.error(f"Error generating itinerary: {e}")
            return self.create_fallback_itinerary(parameters['days'], hotel['name'], parameters['location'])

    def process_itinerary_response(self, content: str) -> List[Dict[str, Any]]:
        """
        Process and validate the itinerary response
        """
        try:
            # First try to parse as-is
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            json_pattern = r'\[\s*\{.*\}\s*\]'
            match = re.search(json_pattern, content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
                    
            # Try to fix with a second agent
            try:
                fix_agent = Agent(
                    model=Gemini(id=self.gemini_model_id),
                    instructions="""
                    Fix this JSON for a travel itinerary. Return ONLY valid JSON with no additional text.
                    The JSON should be an array of day objects, each with: day (number), title (string),
                    activities (array), meals (object), and travel_tips (string).
                    """
                )
                fixed_response = fix_agent.run(f"Fix this travel itinerary JSON: {content}")
                return json.loads(fixed_response.content)
            except Exception as e:
                logger.error(f"Failed to fix JSON: {e}")
                return []

    def create_fallback_itinerary(self, days: int, hotel_name: str, location: str) -> List[Dict[str, Any]]:
        """
        Create a basic fallback itinerary when generation fails
        """
        itinerary = []
        for day in range(1, days + 1):
            itinerary.append({
                "day": day,
                "title": f"Day {day}: Exploring {location}",
                "activities": [
                    {
                        "time": "10:00 AM - 12:00 PM",
                        "name": "Local Sightseeing",
                        "description": f"Explore popular attractions in {location}",
                        "tips": f"Ask the {hotel_name} concierge for recommendations"
                    },
                    {
                        "time": "2:00 PM - 4:00 PM",
                        "name": "Cultural Experience",
                        "description": f"Visit local cultural spots in {location}",
                        "tips": "Check opening hours before visiting"
                    }
                ],
                "meals": {
                    "breakfast": f"Breakfast at {hotel_name}",
                    "lunch": "Try a local restaurant",
                    "dinner": "Dining at a recommended restaurant"
                },
                "travel_tips": "Consider local transportation options or arranging with your hotel"
            })
        return itinerary

    def generate_location_itinerary(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a generic itinerary for a location when no specific hotel is found
        """
        location = parameters['location']
        days = parameters['days']
        budget_note = f" with a budget of {parameters['budget']} INR" if parameters['budget'] else ""
        
        generic_agent = Agent(
            model=Gemini(id=self.gemini_model_id),
            instructions=f"""
            Create a {days}-day travel itinerary for {location}{budget_note}. 
            Your response must be valid JSON following this format:
            [
              {{
                "day": 1,
                "title": "Day 1: [Theme]",
                "activities": [
                  {{
                    "time": "9:00 AM - 11:30 AM",
                    "name": "Activity Name",
                    "description": "Brief description",
                    "tips": "Helpful tips"
                  }}
                ],
                "meals": {{
                  "breakfast": "Recommendation",
                  "lunch": "Recommendation",
                  "dinner": "Recommendation"
                }},
                "travel_tips": "Overall tips"
              }}
            ]
            
            IMPORTANT: Your entire response must be valid JSON with no other text.
            """
        )
        
        try:
            response = generic_agent.run(f"Create a {days}-day travel itinerary for {location}{budget_note}")
            return {
                'success': True,
                'parameters': parameters,
                'itinerary': self.process_itinerary_response(response.content),
                'note': f"Generated a generic itinerary for {location}"
            }
        except Exception as e:
            logger.error(f"Error generating generic itinerary: {e}")
            return {
                'success': False,
                'parameters': parameters,
                'error': f"Could not generate an itinerary for {location}. Please try a different query."
            }

    def plan_travel(self, query: str) -> Dict[str, Any]:
        """
        Primary function to process a travel query and generate a complete travel plan
        
        Args:
            query: Natural language query about travel plans
            
        Returns:
            Dictionary with extracted parameters, hotel information, and generated itinerary
        """
        # Step 1: Extract parameters from the query
        parameters = self.extract_query_parameters(query)
        
        # Step 2: Find hotels matching the parameters
        hotels = self.find_hotels(parameters)
        
        # Step 3: Check budget compatibility and rank hotels
        hotels = self.check_hotel_budget_compatibility(hotels, parameters)
        
        # Step 4: Generate itinerary based on the best hotel match
        if hotels:
            # Use the first (best) hotel match
            hotel = hotels[0]
            
            # Generate the itinerary
            itinerary = self.generate_itinerary(hotel, parameters)
            
            # Build the response
            response = {
                'success': True,
                'parameters': parameters,
                'hotel': hotel,
                'other_options': hotels[1:3] if len(hotels) > 1 else [],  # Include 2 alternatives if available
                'itinerary': itinerary
            }
            
            # Add budget analysis if budget was specified
            if parameters['budget']:
                total_hotel_cost = hotel.get('total_cost', 0)
                response['budget_analysis'] = {
                    'total_budget': parameters['budget'],
                    'hotel_cost': total_hotel_cost,
                    'remaining_budget': parameters['budget'] - total_hotel_cost,
                    'within_budget': hotel.get('within_budget', False)
                }
                
            return response
            
        else:
            # If no hotels found but location is specified, generate a generic itinerary
            if parameters['location']:
                return self.generate_location_itinerary(parameters)
            else:
                # No hotels and no location - return error
                return {
                    'success': False,
                    'parameters': parameters,
                    'error': "Could not find any suitable hotels or locations. Please try a more specific query."
                }


# Main example usage
if __name__ == "__main__":
    # Example query
    query = "suggest me a 7 day itinerary in delhi within a price range of 1 lakh"
    
    # Create planner and process query
    planner = TravelPlanner()
    result = planner.plan_travel(query)
    
    # Display the results
    if result['success']:
        # Show parameters
        print(f"\n===== Travel Plan =====")
        print(f"Location: {result['parameters']['location']}")
        print(f"Duration: {result['parameters']['days']} days")
        if result['parameters']['budget']:
            print(f"Budget: ₹{result['parameters']['budget']:,.0f}")
            
        # Show hotel information if available
        if 'hotel' in result:
            hotel = result['hotel']
            print(f"\n----- Selected Hotel -----")
            print(f"Name: {hotel['name']}")
            print(f"Location: {hotel.get('city', '')}")
            print(f"Rating: {hotel.get('rating', 'N/A')}/5")
            
            if 'price' in hotel:
                total_cost = hotel['price'] * result['parameters']['days']
                print(f"Price: ₹{hotel['price']:,.0f} per night (₹{total_cost:,.0f} total)")
            
            # Show budget analysis if available
            if 'budget_analysis' in result:
                analysis = result['budget_analysis']
                print(f"\n----- Budget Analysis -----")
                print(f"Total budget: ₹{analysis['total_budget']:,.0f}")
                print(f"Hotel cost: ₹{analysis['hotel_cost']:,.0f}")
                print(f"Remaining: ₹{analysis['remaining_budget']:,.0f}")
                if analysis['within_budget']:
                    print("Status: Within budget ✓")
                else:
                    print("Status: Exceeds budget ⚠")
        
        # Show alternative options if available
        if 'other_options' in result and result['other_options']:
            print(f"\n----- Alternative Options -----")
            for i, alt_hotel in enumerate(result['other_options'], 1):
                print(f"{i}. {alt_hotel['name']} - ₹{alt_hotel.get('price', 0):,.0f} per night")
        
        # Show note if present
        if 'note' in result:
            print(f"\nNote: {result['note']}")
        
        # Show itinerary
        print(f"\n===== {result['parameters']['days']}-Day Itinerary =====")
        for day_plan in result['itinerary']:
            print(f"\n{day_plan['title']}")
            
            for activity in day_plan['activities']:
                print(f"  • {activity['time']}: {activity['name']}")
                print(f"    {activity['description']}")
                if 'tips' in activity and activity['tips']:
                    print(f"    Tip: {activity['tips']}")
            
            print(f"\n  Meals:")
            print(f"    Breakfast: {day_plan['meals']['breakfast']}")
            print(f"    Lunch: {day_plan['meals']['lunch']}")
            print(f"    Dinner: {day_plan['meals']['dinner']}")
            
            print(f"\n  Daily Tips: {day_plan['travel_tips']}")
    else:
        print(f"Error: {result['error']}")