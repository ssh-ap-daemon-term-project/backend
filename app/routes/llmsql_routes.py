from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from ..llmsql import LLMSQL

router = APIRouter(
    prefix="/llmsql",
    tags=["llmsql"],
    responses={404: {"description": "Not found"}},
)

class SQLQueryRequest(BaseModel):
    prompt: str

class SQLQueryResponse(BaseModel):
    explanation: str
    sql: str
    result: List[Dict[str, Any]] = None

@router.post("/query", response_model=SQLQueryResponse)
def generate_sql_query(request: SQLQueryRequest):
    """
    Generate and execute SQL based on natural language prompt
    """
    llmsql = LLMSQL()
    try:
        result = llmsql.generate_sql_from_prompt(request.prompt)
        
        # If there was an error, raise an HTTP exception
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    finally:
        llmsql.close()