import ast
import re
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google import Gemini

def _unwrap_metric(x):
    """
    Helper to turn either an int or a single‐element list into an int.
    """
    if isinstance(x, list) and len(x) > 0:
        return x[0]
    return x if isinstance(x, int) else None

def _get_metric(metrics, name):
    if isinstance(metrics, dict):
        return metrics.get(name)
    return getattr(metrics, name, None)

class LocationExtractor:
    def __init__(self, model_id="gemini-3.5-flash-lite"):
        """
        Initializes the Agent for location extraction.
        """
        load_dotenv()
        self.agent = Agent(
            model=Gemini(id=model_id),
            instructions="""
                You are an expert location extractor.
                Your task is to identify and return a list of named locations (e.g., cities, hotels, famous landmarks) from the user's query.
                Only return the names of locations in a Python list format.

                Examples:
                    Query: I want to visit Hyderabad for 7 days, suggest me some plan.
                    Response: ['Hyderabad']

                    Query: Provide near locations of Taj hotel at Mumbai.
                    Response: ['Taj hotel', 'Mumbai']

                    Query: I will go to Goa and then visit the Leela hotel.
                    Response: ['Goa', 'Leela hotel']
            """
        )

    def extract_locations(self, prompt: str):
        """
        Executes the agent to extract location entities and returns a list.
        """
        try:
            response = self.agent.run(prompt)
            # Add token metrics tracking
            input_tokens = _unwrap_metric(_get_metric(response.metrics, 'input_tokens'))
            output_tokens = _unwrap_metric(_get_metric(response.metrics, 'output_tokens'))
            total_tokens = _unwrap_metric(_get_metric(response.metrics, 'total_tokens'))
            print(f"Location extractor metrics - Input tokens: {input_tokens}, Output tokens: {output_tokens}, Total: {total_tokens}")
            
            content = response.content.strip()
            list_match = re.search(r"\[[\s\S]*\]", content)
            locations = ast.literal_eval(list_match.group(0) if list_match else content)
            print(locations)
            if not isinstance(locations, list) or not all(isinstance(location, str) for location in locations):
                raise ValueError("Parsed content is not a list.")
            return [location.strip() for location in locations if location.strip()]
        except (SyntaxError, ValueError) as e:
            print(f"Failed to parse response: {response.content}")
            raise e


if __name__ == "__main__":
    extractor = LocationExtractor()
    prompt = "I want to visit kolkata and go to ITC, then want to travel other destinations, suggest me."
    locations = extractor.extract_locations(prompt)
    print(locations)