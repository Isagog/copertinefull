import base64
import os
from pathlib import Path
import re
from typing import Tuple

from openai import OpenAI

from src.includes.prompts import GPT_PROMPT
from src.includes.utils import init_weaviate_client, setup_logging

logger = setup_logging("logs/gpt_extract")


class ManifestoGPTExtractor:
    def __init__(self):
        self.openai_client = OpenAI()
        self.model_name = os.getenv("COP_VISION_MODELNAME")
        self.images_dir = Path("images")  # Use Path for directories

    def get_image_base64(self, filename: str) -> str:
        """Load image from filesystem and convert to base64."""
        try:
            image_path = self.images_dir / filename
            with image_path.open("rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        except Exception:
            logger.exception("Error loading image %s", filename)
            raise

    def parse_gpt_response(self, response_text: str) -> Tuple[str, str]:
        caption_match = re.search(
            r"CAPTION:\s*(.*?)(?=DESCRIPTION:|$)", response_text, re.DOTALL,
        )
        description_match = re.search(
            r"DESCRIPTION:\s*(.*?)$", response_text, re.DOTALL,
        )
        return (
            caption_match.group(1).strip() if caption_match else "",
            description_match.group(1).strip() if description_match else "",
        )

    def process_object(self, collection, obj) -> None:
        properties = obj.properties
        if properties.get("captionAIStr") or properties.get("imageAIDeStr"):
            return

        try:
            logger.info("Processing object with ID: %s", properties["editionId"])

            # Get image filename and convert to base64
            image_filename = properties["editionImageStr"]
            image_base64 = self.get_image_base64(image_filename)

            # Construct data URL for OpenAI API
            data_url = f"data:image/jpeg;base64,{image_base64}"

            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": GPT_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": data_url,
                                    "detail": "high",
                                },
                            },
                        ],
                    },
                ],
            )

            caption, description = self.parse_gpt_response(
                response.choices[0].message.content,
            )
            collection.data.update(
                uuid=obj.uuid,
                properties={
                    "captionAIStr": caption,
                    "imageAIDeStr": description,
                    "modelAIName": self.model_name,  # Use instance variable instead of env lookup
                },
            )
            logger.info("Successfully updated object %s", properties["editionId"])
        except Exception:
            logger.exception(
                "Error processing object %s", properties.get("editionId", "unknown"),
            )


def main():
    client = init_weaviate_client()
    try:
        collection = client.collections.get(os.getenv("COP_COPERTINE_COLLNAME"))
        extractor = ManifestoGPTExtractor()
        for obj in collection.iterator():
            extractor.process_object(collection, obj)
    finally:
        client.close()


if __name__ == "__main__":
    main()
