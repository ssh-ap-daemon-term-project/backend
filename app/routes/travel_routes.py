from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from ..travel_planner import get_lat_long_of_hotel, websearch_agent
import re

router = APIRouter(
    prefix="/travel",
    tags=["travel"],
    responses={404: {"description": "Not found"}}
)

class TravelQuery(BaseModel):
    query: str

class TravelResponse(BaseModel):
    success: bool
    hotel_name: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None
    itinerary: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

@router.post("/plan", response_model=TravelResponse)
def generate_travel_plan(request: TravelQuery):
    """
    Generate a travel itinerary based on a natural language query.
    
    Examples:
    - "Where can I visit from Taj Hotel in Mumbai for 2 days?"
    - "Create a 3-day plan for The Oberoi Amarvilas"
    - "Suggest places to visit near Leela Palace for 4 days"
    """
    try:
        query = request.query
        
        # Extract hotel name from query with a more flexible pattern
        hotel_pattern = r'(?:from|at|near|around|in)\s+(?:the\s+)?([A-Z][\w\s\']+?)(?:\s+(?:in|for|\.|\?|$))'
        hotel_match = re.search(hotel_pattern, query, re.IGNORECASE)
        hotel_name = hotel_match.group(1).strip() if hotel_match else ""
        
        # Extract number of days if mentioned
        days_match = re.search(r'for (\d+) days?', query)
        days = int(days_match.group(1)) if days_match else 3  # Default to 3 days
        
        # Get latitude and longitude of the hotel
        lat_long = get_lat_long_of_hotel(query)
        
        if lat_long:
            # Get itinerary using web search with the coordinates
            itinerary = websearch_agent(lat_long, hotel_name, days)
            
            return TravelResponse(
                success=True,
                hotel_name=hotel_name,
                coordinates=lat_long,
                itinerary=itinerary
            )
        else:
            # Try to extract place name and generate itinerary based on the place
            place_name = hotel_name if hotel_name else "popular destination"
            
            return TravelResponse(
                success=False,
                hotel_name=hotel_name,
                coordinates=None,
                error=f"Could not find coordinates for {hotel_name}. Please try a different query."
            )
            
    except Exception as e:
        return TravelResponse(
            success=False,
            error=f"Error generating travel plan: {str(e)}"
        )

