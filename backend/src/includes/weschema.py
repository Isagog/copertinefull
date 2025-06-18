# weschema.py
import os

from dotenv import load_dotenv
from weaviate.classes.config import DataType, Property, Tokenization

# Load environment variables from the .env file
load_dotenv()

"""
Property level config
"indexFilterable": true,              // Optional, default is true. By default each property is indexed with a roaring bitmap index where available for efficient filtering.
"indexSearchable": true               // Optional, default is true. By default each property is indexed with a searchable index for BM25-suitable Map index for BM25 or hybrid searching.
"""

# Fetch class names from environment variables
COP_COPERTINE_COLLNAME = os.getenv(
    "COP_COPERTINE_COLLNAME", "Copertine",
)  # Default to "Copertine" if not set

COPERTINE_COLL_CONFIG = {
    "class": COP_COPERTINE_COLLNAME,
    "description": "Collection of Il Manifesto newspaper covers",
    "vectorizer": "none",
    "properties": [
        {
            "name": "testataName",
            "description": "Name of the publication",
            "dataType": ["text"],
            "tokenization": "field",
            "indexSearchable": False,
        },
        {
            "name": "editionId",
            "description": "Unique identifier for the edition",
            "dataType": ["text"],
            "tokenization": "field",
            "indexFilterable": True,
            "indexSearchable": False,
        },
        {
            "name": "editionDateIsoStr",
            "description": "Publication date of the edition",
            "dataType": ["date"],
        },
        {
            "name": "editionImageFnStr",
            "description": "Filename of the edition image",
            "dataType": ["text"],
            "tokenization": "field",
            "indexSearchable": False,
        },
        {
            "name": "captionStr",
            "description": "Text scraped as the caption",
            "dataType": ["text"],
            "indexFilterable": False,
        },
        {
            "name": "kickerStr",
            "description": "Text scraped describing the news",
            "dataType": ["text"],
            "indexFilterable": False,
        },
        {
            "name": "captionAIStr",
            "description": "Text recognized by AI as the caption",
            "dataType": ["text"],
            "indexFilterable": False,
        },
        {
            "name": "imageAIDeStr",
            "description": "AI generated description of the image",
            "dataType": ["text"],
            "indexFilterable": False,
        },
        {
            "name": "modelAIName",
            "description": "Name of the LLM model used for extraction and description",
            "dataType": ["text"],
            "tokenization": "field",
            "indexSearchable": False,
        },
    ],
}
