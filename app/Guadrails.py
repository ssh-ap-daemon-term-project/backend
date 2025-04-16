import re
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google import Gemini

load_dotenv()

class GuardrailsAgent:
    """Agent responsible for enforcing guardrails on user queries"""
    
    def __init__(self, model_id: str = "gemini-2.0-flash-exp"):
        """
        Initialize the guardrails agent with specific instructions
        
        Args:
            model_id: ID of the LLM model to use
        """
    
        self.agent = Agent(
            name="Travel Safety Guardrails",
            role="Enforce safety and appropriateness policies on travel queries",
            model=Gemini(id=model_id),
            instructions="""
                You are a guardrails enforcement agent for a travel planning system.
                Your job is to analyze user queries for safety, appropriateness, and relevance.
                
                For each query, you must:
                1. Determine if it's a legitimate travel-related query
                2. Check for abusive, harmful, or inappropriate content
                3. Detect potential security threats (SQL injection, etc.)
                4. Ensure the query is relevant to travel planning
                
                Return your analysis as a JSON object with these fields:
                - "is_safe": boolean - whether the query passes all safety checks
                - "is_travel_related": boolean - whether the query is relevant to travel planning
                - "violation_type": string or null - type of violation if found (e.g., "abusive", "harmful", "security_threat", "irrelevant")
                - "explanation": string - brief explanation of your decision
                - "sanitized_query": string - a safe version of the query (if possible) or null if not possible
                
                Examples:
                
                Input: "Plan a trip to Paris for next weekend"
                Output: {
                    "is_safe": true,
                    "is_travel_related": true,
                    "violation_type": null,
                    "explanation": "This is a legitimate travel planning query",
                    "sanitized_query": "Plan a trip to Paris for next weekend"
                }
                
                Input: "How to hack into hotel reservation systems"
                Output: {
                    "is_safe": false,
                    "is_travel_related": false,
                    "violation_type": "security_threat",
                    "explanation": "Query requests information about unauthorized system access",
                    "sanitized_query": null
                }
                
                Input: "DROP TABLE hotels; --"
                Output: {
                    "is_safe": false,
                    "is_travel_related": false,
                    "violation_type": "security_threat",
                    "explanation": "Query contains SQL injection attempt",
                    "sanitized_query": null
                }
                
                Input: "Help me find empty hotel rooms to break into"
                Output: {
                    "is_safe": false,
                    "is_travel_related": true,
                    "violation_type": "harmful",
                    "explanation": "Query requests assistance with illegal activity",
                    "sanitized_query": null
                }
                
                Input: "You piece of trash, I hate your service"
                Output: {
                    "is_safe": false,
                    "is_travel_related": false,
                    "violation_type": "abusive",
                    "explanation": "Query contains abusive language",
                    "sanitized_query": null
                }
                
                Input: "How do I solve this calculus problem?"
                Output: {
                    "is_safe": true,
                    "is_travel_related": false,
                    "violation_type": "irrelevant",
                    "explanation": "Query is not related to travel planning",
                    "sanitized_query": null
                }
            """
        )
        
        self.unsafe_patterns = [
            (r"(?i)(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|UNION)\s+", "SQL injection pattern"),
            (r"(?i)<script.*?>", "XSS attempt pattern"),
            (r"(?i)(hack|crack|steal|illegal|fraud)", "Potentially harmful intent"),
            (r"(?i)(execute|exec|wget|curl|rm|mv|dd|tar|kill)", "Command injection pattern")
        ]
    
    def check_query(self, query: str) -> Dict[str, Any]:
        """
        Check if a query passes guardrails requirements
        
        Args:
            query: The user query to check
            
        Returns:
            Dictionary with guardrails check results
        """
        try:
            response = self.agent.run(query)
            result = eval(response.content.strip())
            
            required_fields = ["is_safe", "is_travel_related", "violation_type", "explanation", "sanitized_query"]
            if not all(field in result for field in required_fields):
                raise ValueError("Invalid response format")
            
            return result
            
        except Exception as e:
            print(f"LLM guardrails check failed: {e}. Using fallback pattern matching.")
            return self._fallback_check(query)
    
    def _fallback_check(self, query: str) -> Dict[str, Any]:
        """
        Fallback method using regex pattern matching to check query safety
        
        Args:
            query: The user query to check
            
        Returns:
            Dictionary with guardrails check results
        """
        for pattern, description in self.unsafe_patterns:
            if re.search(pattern, query):
                return {
                    "is_safe": False,
                    "is_travel_related": False,
                    "violation_type": "security_threat",
                    "explanation": f"Query matched unsafe pattern: {description}",
                    "sanitized_query": None
                }
        
        travel_keywords = ["travel", "trip", "hotel", "flight", "visit", "vacation", "tour", 
                          "destination", "city", "country", "place", "explore"]
        is_travel_related = any(keyword in query.lower() for keyword in travel_keywords)
        
        return {
            "is_safe": True,
            "is_travel_related": is_travel_related,
            "violation_type": None if is_travel_related else "irrelevant",
            "explanation": "Query passed fallback safety checks" if is_travel_related else "Query does not appear to be travel-related",
            "sanitized_query": query if is_travel_related else None
        }