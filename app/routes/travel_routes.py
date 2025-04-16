from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from ..travel_planner import TravelPlanningTeam

router = APIRouter(
    responses={404: {"description": "Not found"}},
)

class TravelPlanRequest(BaseModel):
    query: str
    # stream: Optional[bool] = False

class TravelPlanResponse(BaseModel):
    result: str

@router.post("/plan", response_model=TravelPlanResponse)
def generate_travel_plan(request: TravelPlanRequest):
    """
    Generate a travel plan based on natural language query
    """
    try:
        # Initialize the travel planning team
        travel_planner = TravelPlanningTeam()
        
        # Generate the travel plan
        result = travel_planner.generate_travel_plan(
            query=request.query,
            # stream=request.stream
        )
        
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating travel plan: {str(e)}")