import os
from dotenv import load_dotenv

from langchain_community.utilities import SQLDatabase
from langchain_core.tools import tool

load_dotenv()

db = SQLDatabase.from_uri(os.getenv("DATABASE_URL"))

@tool
def db_query_tool(query: str) -> str:
    """
    Execute a SQL query against the database and get back the result.
    If the query is not correct, an error message will be returned.
    If an error is returned, rewrite the query, check the query, and try again.
    """
    result = db.run_no_throw(query)
    if not result:
        return "Error: Query failed. Please rewrite your query and try again."
    return result
