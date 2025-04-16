import psycopg2
import os
import re  # Added missing import for regular expressions
from textwrap import dedent
from psycopg2.extras import RealDictCursor
from typing import List, Optional
from agno.agent import Agent
from agno.models.google import Gemini
from agno.team.team import Team
from agno.tools.googlesearch import GoogleSearchTools
from agno.tools.duckduckgo import DuckDuckGoTools
from app.location_extractor import LocationExtractor
from app.Guardrails import GuardrailsAgent
from app.SQL_queries import sql_queries
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Create a database connection using the DATABASE_URL from environment variables"""
    try:
        conn = psycopg2.connect(
            os.getenv('DATABASE_URL'),
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None
    
def extract_query(query, params=None):
    """Execute a SQL query and return the results"""
    conn = get_db_connection()
    if not conn:
        return "Database connection failed"
    
    try:
        cursor = conn.cursor()
        cursor.execute(query, params if params else ())
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results
    except Exception as e:
        if conn:
            conn.close()
        return f"Query execution error: {e}"



class TravelAgent:
    """Base class for all travel-related agents"""
    
    def __init__(self, name: str, role: str, instructions: str, 
                 model_id: str = "gemini-2.0-flash-exp", 
                 search: bool = False,
                 tools: Optional[List] = None):
        """Initialize a travel agent with specific role and instructions"""
        self.name = name
        self.role = role
        self.instructions = dedent(instructions)
        
        if tools is None:
            tools = []
            
        self.agent = Agent(
            name=name,
            role=role,
            model=Gemini(id=model_id, search=search),
            tools=tools,
            add_name_to_instructions=True,
            instructions=self.instructions,
        )


class DestinationResearcher(TravelAgent):
    """Agent specialized in researching travel destinations"""
    
    def __init__(self):
        super().__init__(
            name="Destination Researcher",
            role="Research travel destinations and attractions",
            tools=[GoogleSearchTools(), DuckDuckGoTools()],
            instructions="""
                You are a destination researcher specializing in travel information.
                You will research potential travel destinations based on the traveler's preferences.
                Find information about popular attractions, local culture, best times to visit,
                and unique experiences in each location.
                Provide balanced information about both tourist hotspots and off-the-beaten-path experiences.
            """
        )


class AccommodationExpert(TravelAgent):
    """Agent specialized in finding and evaluating accommodations"""
    
    def __init__(self):
        super().__init__(
            name="Accommodation Expert",
            role="Find and evaluate accommodation options",
            tools=[GoogleSearchTools(), DuckDuckGoTools()],
            instructions="""
                You are an accommodation expert.
                You will research and recommend accommodation options based on the traveler's preferences and budget.
                Consider hotels, vacation rentals, hostels, and unique lodging options.
                Evaluate options based on location, amenities, reviews, price, and accessibility.
                Provide specific recommendations with brief explanations of their advantages.
            """
        )


class TransportationPlanner(TravelAgent):
    """Agent specialized in planning transportation"""
    
    def __init__(self):
        super().__init__(
            name="Transportation Planner",
            role="Plan transportation between and within destinations",
            tools=[GoogleSearchTools()],
            instructions="""
                You are a transportation planning specialist.
                You will research and recommend transportation options between destinations and for local travel.
                Consider flights, trains, buses, car rentals, and public transportation.
                Evaluate options based on cost, convenience, travel time, and environmental impact.
                Provide specific recommendations with estimated travel times and costs.
            """
        )


class LocalExperienceCurator(TravelAgent):
    """Agent specialized in curating local experiences"""
    
    def __init__(self):
        super().__init__(
            name="Local Experience Curator",
            role="Curate authentic local experiences and activities",
            tools=[DuckDuckGoTools()],
            instructions="""
                You are a local experience curator.
                You will research and recommend authentic local experiences, food, and activities.
                Focus on unique cultural experiences, local cuisine, festivals, and events.
                Consider the traveler's interests and preferences when making recommendations.
                Provide specific recommendations with brief explanations of their cultural significance.
            """
        )


class TravelPlanningTeam:
    """Manages a team of travel planning agents"""
    
    def __init__(self):
        load_dotenv()
        self.total_queries = 0
        self.rejected_queries = 0
        self.sanitized_queries = 0
        self.destination_researcher = DestinationResearcher()
        self.accommodation_expert = AccommodationExpert()
        self.transportation_planner = TransportationPlanner()
        self.local_experience_curator = LocalExperienceCurator()
        self.location_extractor = LocationExtractor()
        self.guardrails_agent = GuardrailsAgent()
        self.team = Team(
            name="Travel Planning Team",
            mode="collaborate",
            model=Gemini(id="gemini-1.5-flash"),
            members=[
                self.destination_researcher.agent,
                self.accommodation_expert.agent,
                self.transportation_planner.agent,
                self.local_experience_curator.agent,
            ],
            instructions=[
                "You are a travel planning coordinator.",
                "Coordinate the team to create a comprehensive travel plan based on the traveler's preferences.",
                "Ensure all aspects of the trip (destination, accommodation, transportation, activities) are addressed.",
                "Synthesize the team's input into a cohesive travel itinerary.",
                "You have to stop the discussion when you think the team has developed a complete travel plan."
            ],
            success_criteria="A comprehensive travel plan has been created that meets the traveler's preferences and constraints.",
            share_member_interactions=True,
            markdown=False,
        )
    
    def generate_travel_plan(self, query: str, stream: bool = True) -> str:
        """Generate a detailed travel plan based on the user's query and the database"""
        locations = self.location_extractor.extract_locations(query)
        self.total_queries += 1
        guardrails_result = self.guardrails_agent.check_query(query)
        
        if not guardrails_result["is_safe"]:
            self.rejected_queries += 1
            violation_type = guardrails_result["violation_type"]
            explanation = guardrails_result["explanation"]
            
            rejection_messages = {
                "abusive": "I'm unable to process requests with abusive language. Please rephrase your query with respectful language.",
                "harmful": "I cannot assist with potentially harmful activities. Please submit a query for legitimate travel planning.",
                "security_threat": "Your query has been flagged as a potential security threat. Please submit a legitimate travel planning request.",
                "irrelevant": "This service is specifically for travel planning. Please submit a travel-related query."
            }
            
            message = rejection_messages.get(violation_type, "I'm unable to process this request due to safety concerns.")
            return message
        else:
            effective_query = query
            if guardrails_result.get("sanitized_query"):
                effective_query = guardrails_result["sanitized_query"]
                self.sanitized_queries += 1
            
            # Extract critical information for better planning
            days_pattern = r'(\d+)\s*(?:day|days)'
            days_match = re.search(days_pattern, effective_query, re.IGNORECASE)
            trip_days = int(days_match.group(1)) if days_match else 3  # Default to 3 days if not specified
            
            budget_pattern = r'(?:budget|price|cost|range|under|within)\s*(?:of|:)?\s*(?:Rs\.?|INR|₹)?\s*(\d[\d,]*)'
            budget_match = re.search(budget_pattern, effective_query, re.IGNORECASE)
            budget = int(budget_match.group(1).replace(',', '')) if budget_match else None
            
            interests = []
            if "histor" in effective_query.lower():
                interests.append("historical sites")
            if any(word in effective_query.lower() for word in ["beach", "sea", "ocean", "water"]):
                interests.append("beaches")
            if any(word in effective_query.lower() for word in ["museum", "art", "culture"]):
                interests.append("museums and cultural attractions")
            if any(word in effective_query.lower() for word in ["food", "cuisine", "restaurant", "eat"]):
                interests.append("food experiences")
            if any(word in effective_query.lower() for word in ["adventure", "hik", "trek", "outdoor"]):
                interests.append("outdoor adventures")
            if any(word in effective_query.lower() for word in ["shop", "mall", "market"]):
                interests.append("shopping")
            
            # Extract database information for hotels and other services
            extracted_info = []
            for raw_sql in sql_queries:
                for loc in locations:
                    formatted_sql = raw_sql
                    formatted_sql = formatted_sql.replace(":city", f"'{loc}'")
                    formatted_sql = formatted_sql.replace(":hotel_name", f"'{loc}'")
                    
                    response = extract_query(raw_sql, (loc,))
                    print(response)
                    if response and response != "Database connection failed" and not isinstance(response, str):
                        extracted_info.append({
                            "location": loc,
                            "query": raw_sql,
                            "result": response
                        })

            # Build a structured prompt for the agents to use the database insights effectively
            prompt_template = f"""
    You are a team of expert travel planning agents collaborating to prepare a tailored travel plan.

    User Query:
    ------------
    {effective_query}

    Trip Parameters:
    ---------------
    - Main Location(s): {', '.join(locations) if locations else 'Not specified'}
    - Duration: {trip_days} days
    - Budget: {"INR " + str(budget) if budget else "Not specified"}
    - Interests: {', '.join(interests) if interests else 'General sightseeing'}

    Extracted Database Insights:
    ----------------------------
    """
            for info in extracted_info:
                prompt_template += f"\n[Location: {info['location']}]\nSQL: {info['query']}\nResult: {info['result']}\n"

            prompt_template += """

    Instructions:
    -------------
    1. Create a DETAILED day-by-day itinerary with SPECIFIC NAMED places to visit (not generic "local markets" but actual names like "Crawford Market in Mumbai").

    2. Prioritize web search to find:
    - SPECIFIC tourist attractions with actual names (e.g., "Gateway of India", "Elephanta Caves")
    - SPECIFIC local restaurants with names (e.g., "Trishna Restaurant for seafood")
    - SPECIFIC shopping locations with names (e.g., "Colaba Causeway Market")
    - SPECIFIC cultural events or experiences with names when possible

    3. For each day:
    - Provide a morning, afternoon, and evening breakdown
    - List SPECIFIC places to visit with brief descriptions
    - Include estimated time spent at each location
    - Suggest specific local food options for each meal
    - Include transportation recommendations between locations

    4. For accommodation:
    - Use database information on hotels when available
    - Augment with web search to provide SPECIFIC hotel recommendations with names
    - Include brief descriptions of amenities and approximate pricing
    - Recommend specific room types based on the traveler's needs

    5. For transportation:
    - Provide SPECIFIC transportation options with names (e.g., "Uber", "Mumbai Metro", "BEST Bus routes")
    - Include estimated costs for transportation
    - Suggest the most efficient routes between attractions

    6. Practical Tips:
    - Include weather considerations for the time of year
    - Mention any local customs or etiquette important for travelers
    - Include safety tips specific to the destination
    - Suggest specific local phrases that might be helpful

    Remember:
    - ALWAYS provide SPECIFIC NAMED locations, not generic descriptions
    - Use the database information where available but greatly augment with web search
    - Format the response as a detailed, day-by-day itinerary
    - Don't mention that you're using database information in your response
    - If information is limited, use web search to fill in the gaps comprehensively
    - Make real-world, actionable recommendations with specific place names throughout
    """

            answer = self.team.run(message=prompt_template)
            return answer.content


if __name__ == "__main__":
    travel_planner = TravelPlanningTeam()    
    result = travel_planner.generate_travel_plan(
        query="suggest me some hotels in Mumbai within price range of 10000 for 2 days",
    )
    print(result)