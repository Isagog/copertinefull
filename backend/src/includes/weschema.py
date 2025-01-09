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
        Property(
            name="testataName",
            description="Name of the publication",
            data_type=DataType.TEXT,
            tokenization=Tokenization.FIELD,
            index_searchable=False,
        ),
        Property(
            name="editionId",
            description="Unique identifier for the edition",
            data_type=DataType.TEXT,
            tokenization=Tokenization.FIELD,
            index_searchable=False,
        ),
        Property(
            name="editionDateIsoStr",
            description="Publication date of the edition",
            data_type=DataType.DATE,
        ),
        Property(
            name="editionImageFnStr",
            description="Filename of the edition image",
            data_type=DataType.TEXT,
            tokenization=Tokenization.FIELD,
            index_searchable=False,
        ),
        Property(
            name="captionStr",
            description="Text scraped as the caption",
            data_type=DataType.TEXT,
            index_filterable=False,
        ),
        Property(
            name="kickerStr",
            description="Text scraped describing the news",
            data_type=DataType.TEXT,
            index_filterable=False,
        ),
        Property(
            name="captionAIStr",
            description="Text recognized by AI as the caption",
            data_type=DataType.TEXT,
            index_filterable=False,
        ),
        Property(
            name="imageAIDeStr",
            description="AI generated description of the image",
            data_type=DataType.TEXT,
            index_filterable=False,
        ),
        Property(
            name="modelAIName",
            description="Name of the LLM model used for extraction and description",
            data_type=DataType.TEXT,
            tokenization=Tokenization.FIELD,
            index_searchable=False,
        ),
    ],
}
