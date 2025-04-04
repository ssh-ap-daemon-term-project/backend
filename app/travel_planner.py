from textwrap import dedent
from typing import List, Optional
from agno.agent import Agent
from agno.models.google import Gemini
from agno.team.team import Team
from agno.tools.googlesearch import GoogleSearchTools
from agno.tools.duckduckgo import DuckDuckGoTools
from dotenv import load_dotenv

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
        
        self.destination_researcher = DestinationResearcher()
        self.accommodation_expert = AccommodationExpert()
        self.transportation_planner = TransportationPlanner()
        self.local_experience_curator = LocalExperienceCurator()
        
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
        """Generate a travel plan based on the user's query"""
        answer = self.team.run(
            message=query,
        )
        return answer.content


if __name__ == "__main__":
    travel_planner = TravelPlanningTeam()    
    result = travel_planner.generate_travel_plan(
        query="Tell me about nearest tourist locations of 28.7 degrees N and 77.1 degrees E",
    )
    print(result)