# includes/mytypes.py
from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class Copertina(BaseModel):
    testataName: str = Field("Il Manifesto", description="Name of the publication")
    editionId: str = Field(..., description="Unique identifier for the edition")
    editionDateIsoStr: date = Field(..., description="Publication date of the edition")
    editionImageFnStr: str = Field(..., description="Filename of the edition image")
    captionStr: str = Field(..., description="Text scraped as the caption")
    kickerStr: str = Field(..., description="Text scraped describing the news")

    model_config = {
        "json_schema_extra": {
            "properties": {
                "testataName": {"we_tok": "FIELD", "we_search": False},
                "editionId": {"we_tok": "FIELD", "we_search": False},
                "editionImageFnStr": {"we_tok": "FIELD", "we_search": False},
                "captionStr": {"we_filter": False},
                "kickerStr": {"we_filter": False},
            },
        },
    }

    def model_dump(self, **kwargs) -> dict[str, Any]:
        data = super().model_dump(**kwargs)
        # Convert date to RFC3339 format
        data["editionDateIsoStr"] = f"{data['editionDateIsoStr'].isoformat()}T00:00:00Z"
        return data


class CopertinExtract(Copertina):
    captionAIStr: str = Field(description="Text recognized by AI as the caption")
    imageAIDeStr: str = Field(description="AI generated description of the image")
    modelAIName: str = Field(description="Name of the LLM model used for extraction and description")

    model_config = {
        "json_schema_extra": {
            "properties": {
                **Copertina.model_config["json_schema_extra"]["properties"],
                "captionAIStr": {"we_filter": False},
                "imageAIDeStr": {"we_filter": False},
                "modelAIName": {"we_tok": "FIELD", "we_search": False},
            },
        },
    }
