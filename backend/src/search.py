"""FastAPI endpoint for searching Copertine objects."""

from datetime import date
from typing import List

from fastapi import FastAPI, HTTPException, Query

from includes.mytypes import Copertina

app = FastAPI()

# Mock function for querying the database (Weaviate)
def query_copertine(search: str, mode: str) -> List[Copertina]:
    """Query the database for Copertine objects matching search criteria.

    Args:
        search: Search term to match against Copertine objects
        mode: Search mode, either 'literal' or 'fuzzy'

    Returns:
        List of matching Copertina objects
        
    Raises:
        ValueError: If mode is not 'literal' or 'fuzzy'
    """
    if mode not in ["literal", "fuzzy"]:
        raise ValueError("Invalid mode. Must be 'literal' or 'fuzzy'.")

    # Mock response using the actual Copertina model structure
    return [
        Copertina(
            editionId="2024-01-14",
            editionDateIsoStr=date(2024, 1, 14).isoformat(),
            editionImageFnStr="front-page-2024-01-14.jpg",
            captionStr="Sample caption for the front page",
            kickerStr="Breaking news headline",
        )
    ]

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
