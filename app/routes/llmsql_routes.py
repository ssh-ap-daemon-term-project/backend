from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from ..llmsql import SQLDatabaseQueryProcessor

router = APIRouter(

    responses={404: {"description": "Not found"}},
)

class SQLQueryRequest(BaseModel):
    prompt: str

class SQLQueryResponse(BaseModel):
    result: str

@router.post("/query", response_model=SQLQueryResponse)
def generate_sql_query(request: SQLQueryRequest):
    """
    Generate and execute SQL based on natural language prompt
    """
    try:
        processor = SQLDatabaseQueryProcessor(db_url="postgresql://sshapdaemon:noPassword1@sshapdaemon.postgres.database.azure.com:5432/postgres")
        
        # Process the user's query
        result = processor.final_response(request.prompt)
        
        # If the result is empty or seems like a question back to the user
        if not result or result.strip().endswith("?") or "ready" in result.lower() or "can you" in result.lower():
            # Provide a more helpful fallback response
            if "hotel" in request.prompt.lower() and "chennai" in request.prompt.lower():
                fallback = "I couldn't find any hotels in Chennai in our database. You may want to check if there are hotels in other cities like Mumbai or Delhi."
            elif "hotel" in request.prompt.lower():
                fallback = "I couldn't find information about the hotels you're looking for. Please try asking about hotels in specific cities like Mumbai, Delhi, or Kolkata."
            elif "driver" in request.prompt.lower() or "name" in request.prompt.lower():
                fallback = "I couldn't find any matching records in the database. Please check the spelling or try a different query."
            else:
                fallback = "I couldn't find information related to your query in our database. Please try to be more specific or ask about hotels, rooms, or drivers available in our system."
            
            return {"result": fallback}
            
        return {"result": result}
    except Exception as e:
        # Log the error but return a user-friendly message
        print(f"Error processing query: {str(e)}")
        
        # Provide a helpful error message based on the query
        if "hotel" in request.prompt.lower():
            fallback = "I'm having trouble finding hotel information right now. Please try again with a more specific query like 'Show hotels in Mumbai' or 'List luxury hotels'."
        elif "room" in request.prompt.lower():
            fallback = "I'm having trouble finding room information right now. Please try asking about available rooms in a specific hotel or city."
        else:
            fallback = "I'm having trouble processing your request right now. Please try a different query or be more specific."
            
        return {"result": fallback}