# types.py
from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class Copertina(BaseModel):
    testataName: str = Field("Il Manifesto", description="Name of the publication", we_tok="FIELD", we_search=False)
    editionId: str = Field(..., description="Unique identifier for the edition", we_tok="FIELD", we_search=False)
    editionDateIsoStr: date = Field(..., description="Publication date of the edition")
    editionImageFnStr: str = Field(..., description="Filename of the edition image", we_tok="FIELD", we_search=False)
    captionStr: str = Field(..., description="Text scraped as the caption", we_filter=False)
    kickerStr: str = Field(..., description="Text scraped describing the news", we_filter=False)

    def model_dump(self, **kwargs) -> dict[str, Any]:
        data = super().model_dump(**kwargs)
        # Convert date to RFC3339 format
        data["editionDateIsoStr"] = f"{data['editionDateIsoStr'].isoformat()}T00:00:00Z"
        return data

class CopertinExtract(Copertina):
    captionAIStr: str = Field(description="Text recognized by AI as the caption", we_filter=False)
    imageAIDeStr: str = Field(description="AI generated description of the image", we_filter=False)
    modelAIName: str = Field(description="Name of the LLM model used for extraction and description", we_tok="FIELD", we_search=False)
