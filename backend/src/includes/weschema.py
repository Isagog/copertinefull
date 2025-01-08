# weschema.py
import os
from dotenv import load_dotenv
from weaviate.classes.config import Property, DataType, Tokenization

# Load environment variables from the .env file
load_dotenv()

# Fetch class names from environment variables
COP_COPERTINE_COLLNAME = os.getenv("COP_COPERTINE_COLLNAME", "Copertine")  # Default to "Copertine" if not set

COPERTINE_COLL_CONFIG = {
    "class": COP_COPERTINE_COLLNAME,
    "description": "Collection of Il Manifesto newspaper covers",
    "vectorizer": "none",
    "properties": [
        Property(
            name="testataName",
            description="Name of the  magazine. e.g. Il Manifesto",
            data_type=DataType.TEXT,
            tokenization=Tokenization.FIELD,
            index_searchable=False
        ),
        Property(
            name="editionId",
            description="Unique identifier for the edition",
            data_type=DataType.TEXT,
            tokenization=Tokenization.FIELD,
            index_searchable=False
        ),
        Property(
            name="editionImageStr",
            description="Image filename",
            data_type=DataType.TEXT,
            tokenization=Tokenization.FIELD,
            index_searchable=False
        ),
        Property(
            name="editionDateIsoStr",
            description="Publication date of the edition",
            data_type=DataType.DATE
        ),
        Property(
            name="captionAIStr",
            description="Image caption as recognized by the AI model",
            data_type=DataType.TEXT
        ),
        Property(
            name="imageAIDeStr",
            description="Image description as generated by the AI model",
            data_type=DataType.TEXT
        ),
        Property(
            name="modelAIName",
            description="AI model name",
            data_type=DataType.TEXT,
            tokenization=Tokenization.FIELD,
            index_searchable=False
        )
    ]
}