# types.py
from pydantic import BaseModel, Field
from datetime import date
from typing import Any

class Copertina(BaseModel):
    testataName: str = Field(..., description="Name of the publication")
    editionId: str = Field(..., description="Unique identifier for the edition")
    editionDateIsoStr: date = Field(..., description="Publication date of the edition")
    editionImageStr: str = Field(..., description="Filename of the edition image")

    def model_dump(self, **kwargs) -> dict[str, Any]:
        data = super().model_dump(**kwargs)
        # Convert date to RFC3339 format
        data['editionDateIsoStr'] = f"{data['editionDateIsoStr'].isoformat()}T00:00:00Z"
        return data
    
class CopertinExtract(Copertina):
    captionAIStr: str = Field(..., description="Text recognized as the caption")
    imageAIDeStr: str = Field(..., description="AI generated description of the image")
    modelAIName: str = Field(..., description="Name of the model used for extraction and description")