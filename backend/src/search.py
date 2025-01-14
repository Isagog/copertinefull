"""FastAPI endpoint for searching Copertine objects."""

from typing import List

from fastapi import FastAPI, HTTPException, Query
import weaviate.exceptions

from includes.mytypes import Copertina
from includes.utils import init_weaviate_client, WeaviateClientInitializationError

app = FastAPI()
client = init_weaviate_client()
def query_copertine(search: str, mode: str) -> List[Copertina]:
    """Query the Weaviate database for Copertine objects matching search criteria.

    Args:
        search: Search term to match against Copertine objects
        mode: Search mode, either 'literal' or 'fuzzy'

    Returns:
        List of matching Copertina objects
        
    Raises:
        ValueError: If mode is not 'literal' or 'fuzzy'
        WeaviateClientInitializationError: If Weaviate client fails
    """
    if mode not in ["literal", "fuzzy"]:
        raise ValueError("Invalid mode. Must be 'literal' or 'fuzzy'.")

    # Configure search properties based on mode
    properties = ["editionId", "editionDateIsoStr", "editionImageFnStr", 
                 "captionStr", "kickerStr", "testataName"]
    
    try:
        # Build query based on search mode
        query = client.query.get("Copertine", properties)
        
        if mode == "fuzzy":
            query = query.with_near_text({"concepts": [search]})
        else:
            # Literal search across multiple fields
            query = query.with_where({
                "operator": "Or",
                "operands": [
                    {
                        "path": ["captionStr"],
                        "operator": "Like",
                        "valueText": f"*{search}*"
                    },
                    {
                        "path": ["kickerStr"],
                        "operator": "Like",
                        "valueText": f"*{search}*"
                    }
                ]
            })

        # Execute query and get results
        result = query.do()
        
        # Convert results to Copertina objects
        copertine = []
        for item in result["data"]["Get"]["Copertine"]:
            copertine.append(Copertina(**item))
        
        return copertine

    except weaviate.exceptions.WeaviateQueryError as e:
        raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/v1/copertine", response_model=List[Copertina])
async def get_copertine(
    search: str = Query(..., description="Search term for copertine objects"),
    mode: str = Query(..., description="Search mode: 'literal' or 'fuzzy'"),
):
    """
    Fetch copertine objects based on a search term and mode.

    The response will include front page entries with their edition IDs, 
    dates, images, captions, and kicker text.
    """
    try:
        copertine = query_copertine(search, mode)
        return copertine
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
