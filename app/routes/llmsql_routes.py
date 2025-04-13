from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
# from ..llmsql import LLMSQLAgent

router = APIRouter(
    prefix="/llmsql",
    tags=["llmsql"],
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
        llmsql_agent = LLMSQLAgent()
        result = llmsql_agent.query_hotels(request.prompt)
        
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")