# includes/mytypes.py
from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class Copertina(BaseModel):
    testata_name: str = Field("Il Manifesto", description="Name of the publication")
    edition_id: str = Field(..., description="Unique identifier for the edition")
    edition_date_iso_str: date = Field(..., description="Publication date of the edition")
    edition_image_fn_str: str = Field(..., description="Filename of the edition image")
    caption_str: str = Field(..., description="Text scraped as the caption")
    kicker_str: str = Field(..., description="Text scraped describing the news")

    model_config = {
        "json_schema_extra": {
            "properties": {
                "testata_name": {"we_tok": "FIELD", "we_search": False},
                "edition_id": {"we_tok": "FIELD", "we_search": False},
                "edition_image_fn_str": {"we_tok": "FIELD", "we_search": False},
                "caption_str": {"we_filter": False},
                "kicker_str": {"we_filter": False},
            },
        },
    }

    def model_dump(self, **kwargs) -> dict[str, Any]:
        data = super().model_dump(**kwargs)
        # Convert date to RFC3339 format
        data["edition_date_iso_str"] = f"{data['edition_date_iso_str'].isoformat()}T00:00:00Z"
        return data


class CopertinExtract(Copertina):
    caption_ai_str: str = Field(description="Text recognized by AI as the caption")
    image_ai_de_str: str = Field(description="AI generated description of the image")
    model_ai_name: str = Field(description="Name of the LLM model used for extraction and description")

    model_config = {
        "json_schema_extra": {
            "properties": {
                **Copertina.model_config["json_schema_extra"]["properties"],
                "caption_ai_str": {"we_filter": False},
                "image_ai_de_str": {"we_filter": False},
                "model_ai_name": {"we_tok": "FIELD", "we_search": False},
            },
        },
    }
