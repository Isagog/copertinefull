import weaviate
from typing import Optional

def get_weaviate_client() -> weaviate.Client:
    """Get a configured Weaviate client."""
    client = weaviate.Client(
        url="http://localhost:8080",  # Default Weaviate instance URL
    )
    return client

def init_schema(client: Optional[weaviate.Client] = None) -> None:
    """Initialize the Weaviate schema if it doesn't exist."""
    if client is None:
        client = get_weaviate_client()

    # Check if schema exists
    schema = client.schema.get()
    if any(cls['class'] == 'Copertine' for cls in schema['classes']):
        return

    # Define schema for Copertine
    copertine_class = {
        'class': 'Copertine',
        'description': 'Schema for Il Manifesto covers',
        'properties': [
            {
                'name': 'captionStr',
                'dataType': ['text'],
                'description': 'The caption text of the cover'
            },
            {
                'name': 'editionDateIsoStr',
                'dataType': ['date'],
                'description': 'The publication date of the edition'
            },
            {
                'name': 'editionId',
                'dataType': ['string'],
                'description': 'Unique identifier for the edition'
            },
            {
                'name': 'editionImageFnStr',
                'dataType': ['string'],
                'description': 'Filename of the cover image'
            },
            {
                'name': 'kickerStr',
                'dataType': ['text'],
                'description': 'The kicker text of the cover'
            },
            {
                'name': 'testataName',
                'dataType': ['string'],
                'description': 'The name of the publication'
            }
        ]
    }

    # Create schema
    client.schema.create_class(copertine_class)
