from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any
from ..includes.database import get_db
from ..includes.auth import get_current_user
from ..includes.models import User
from ..includes.weschema import get_weaviate_client

router = APIRouter(prefix="/copertine", tags=["copertine"])

@router.get("")
async def get_copertine(
    offset: int = 0,
    limit: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    try:
        client = get_weaviate_client()
        
        # GraphQL query with proper Python string
        query = """
        {
            Get {
                Copertine(
                    offset: $offset
                    limit: $limit
                    sort: [{
                        path: ["editionDateIsoStr"]
                        order: desc
                    }]
                ) {
                    captionStr
                    editionDateIsoStr
                    editionId
                    editionImageFnStr
                    kickerStr
                    testataName
                }
            }
        }
        """
        
        # Execute Weaviate queries
        result = client.query.raw(query, {"offset": offset, "limit": limit})

        # Get total count
        count_query = """
        {
            Aggregate {
                Copertine {
                    meta {
                        count
                    }
                }
            }
        }
        """
        count_result = client.query.raw(count_query)

        if not result.get('data') or not result['data'].get('Get') or not result['data']['Get'].get('Copertine'):
            return {
                'data': [],
                'pagination': {
                    'total': 0,
                    'offset': offset,
                    'limit': limit,
                    'hasMore': False
                }
            }

        # Transform the data for the frontend
        mapped_data = [{
            'extracted_caption': item['captionStr'],
            'kickerStr': item['kickerStr'],
            'date': item['editionDateIsoStr'],
            'filename': item['editionImageFnStr'],
            'isoDate': item['editionDateIsoStr']
        } for item in result['data']['Get']['Copertine']]

        total = count_result['data']['Aggregate']['Copertine'][0]['meta']['count']

        return {
            'data': mapped_data,
            'pagination': {
                'total': total,
                'offset': offset,
                'limit': limit,
                'hasMore': offset + limit < total
            }
        }
    except Exception as e:
        print(f"Error fetching copertine: {str(e)}")  # Add logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch copertine: {str(e)}"
        )
