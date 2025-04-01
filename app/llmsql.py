from sqlalchemy import text
from typing import List, Dict, Any, Optional
import os
from openai import OpenAI
from dotenv import load_dotenv
from .database import SessionLocal
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure OpenAI API
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class LLMSQL:
    def __init__(self):
        """Initialize the LLMSQL component"""
        self.db = SessionLocal()
        
    def __enter__(self):
        """Context manager entry"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        
    def close(self):
        """Close database session"""
        if hasattr(self, 'db') and self.db:
            self.db.close()
            self.db = None
        
    def _get_schema_info(self) -> str:
        """Retrieve database schema information for context"""
        schema_query = text("""
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
        """)
        
        try:
            result = self.db.execute(schema_query)
            schema_info = []
            current_table = None
            table_columns = []
            
            for row in result:
                table_name, column_name, data_type = row
                
                if current_table != table_name:
                    if current_table is not None:
                        schema_info.append(f"Table: {current_table}\nColumns: {', '.join(table_columns)}\n")
                    current_table = table_name
                    table_columns = []
                
                table_columns.append(f"{column_name} ({data_type})")
            
            # Add the last table
            if current_table is not None:
                schema_info.append(f"Table: {current_table}\nColumns: {', '.join(table_columns)}\n")
                
            return "\n".join(schema_info)
        except Exception as e:
            logger.error(f"Error fetching schema: {str(e)}")
            return "Error retrieving schema information"
    
    def generate_sql_from_prompt(self, user_prompt: str) -> Dict[str, Any]:
        """
        Generate SQL query from natural language prompt
        
        Args:
            user_prompt: Natural language query from user
            
        Returns:
            Dictionary with SQL query and result
        """
        schema_info = self._get_schema_info()
        
        try:
            # Create a prompt for the LLM with emphasis on case sensitivity
            system_message = f"""You are an assistant that converts natural language to SQL queries.
            Here is the database schema:
            {schema_info}
            
            Generate a PostgreSQL query based on the user's request. 
            You MUST use LOWERCASE for all column names to ensure compatibility.
            DO NOT use camelCase or double quotes in column names.
            
            Return your response as a valid JSON with this structure:
            {{
                "explanation": "Brief explanation of what the query does",
                "sql": "The SQL query with all lowercase column names"
            }}
            
            Example of correct SQL:
            SELECT * FROM hotels JOIN rooms ON hotels.id = rooms.hotelid WHERE hotels.city = 'Mumbai';
            
            Ensure the SQL is valid PostgreSQL syntax with lowercase column names.
            """
            
            # Call OpenAI API to generate SQL
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Keep temperature low for more deterministic responses
                max_tokens=1000
            )
            
            # Extract the response and parse the JSON
            llm_response = response.choices[0].message.content
            result = json.loads(llm_response)
            
            # Execute the modified SQL query
            sql_query = self._make_case_insensitive_sql(result["sql"])
            
            logger.info(f"Original SQL: {result['sql']}")
            logger.info(f"Modified SQL: {sql_query}")
            
            query_result = self._execute_sql(sql_query)
            
            return {
                "explanation": result["explanation"],
                "sql": sql_query,
                "result": query_result
            }
            
        except Exception as e:
            logger.error(f"Error generating SQL: {str(e)}")
            return {
                "error": str(e),
                "explanation": "Failed to generate or execute SQL query",
                "sql": None,
                "result": None
            }
    
    def _make_case_insensitive_sql(self, sql: str) -> str:
        """
        A simpler approach - just use a PostgreSQL setting to make column names case-insensitive
        """
        # Add set command at beginning of query
        return "SET SESSION quote_all_identifiers = OFF; " + sql
    
    def _execute_sql(self, sql_query: str) -> List[Dict[str, Any]]:
        """Execute the generated SQL query and return results"""
        try:
            # Execute the query
            result = self.db.execute(text(sql_query))
            
            # Convert result to a list of dictionaries
            rows = []
            if hasattr(result, 'keys'):
                columns = result.keys()
                for row in result:
                    rows.append({column: value for column, value in zip(columns, row)})
            
            # Commit for write operations
            if not sql_query.strip().lower().startswith('select'):
                self.db.commit()
            
            return rows
        except Exception as e:
            # Rollback in case of error
            self.db.rollback()
            logger.error(f"Error executing SQL: {str(e)}")
            raise