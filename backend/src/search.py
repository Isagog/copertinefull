"""FastAPI endpoint for searching Copertine objects."""

from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException, Query
import weaviate.exceptions

from includes.mytypes import Copertina
from includes.utils import init_weaviate_client


# Create FastAPI lifespan to handle client cleanup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize on startup
    app.state.weaviate_client = init_weaviate_client()
    yield
    # Cleanup on shutdown
    app.state.weaviate_client.close()

app = FastAPI(lifespan=lifespan)

# Error messages as constants
INVALID_MODE_ERROR = "Invalid mode. Must be 'literal' or 'fuzzy'."

def query_copertine(client, searchstr: str, mode: str) -> List[Copertina]:
    """Query the Weaviate database for Copertine objects matching search criteria.

    Args:
        client: Weaviate client instance
        search: Search term to match against Copertine objects
        mode: Search mode, either 'literal' or 'fuzzy'

    Returns:
        List of matching Copertina objects

    Raises:
        ValueError: If mode is not 'literal' or 'fuzzy'
        HTTPException: If database query fails
    """
    if mode not in ["literal", "fuzzy"]:
        raise ValueError(INVALID_MODE_ERROR)

    try:
        copcoll = client.collections.get("Copertine")

        if mode == "fuzzy":
            # Fuzzy search using vector similarity
            response = copcoll.query.near_text(
                query=searchstr,
                limit=30,
            )
        else:
            # Literal search using BM25
            response = copcoll.query.bm25(
                query=searchstr,
                limit=30,
            )

        # Convert response objects to Copertina models
        copertine = []
        for obj in response.objects:
            # Create Copertina object from properties
            copertina = Copertina(**obj.properties)
            copertine.append(copertina)
        return copertine

    except weaviate.exceptions.WeaviateQueryError as e:
        error_msg = repr(e) if not str(e) else str(e)
        raise HTTPException(
            status_code=400,
            detail=f"Query error: {error_msg}",
        ) from e
    except Exception as e:
        error_msg = repr(e) if not str(e) else str(e)
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {error_msg}",
        ) from e


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
        return query_copertine(app.state.weaviate_client, search, mode)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
