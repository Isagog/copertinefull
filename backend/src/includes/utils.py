from datetime import datetime, timezone
import logging
import os
from typing import Optional

from dotenv import load_dotenv
import weaviate


class WeaviateClientInitializationError(Exception):
    """Custom exception for Weaviate client initialization errors."""


def setup_logging(name: str) -> logging.Logger:
    """Configure and return a logger."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(f"{name}.log"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger(name)


def init_weaviate_client() -> weaviate.WeaviateClient:
    """Initialize Weaviate client with error handling."""
    load_dotenv()
    try:
        if os.getenv("COP_WEAVIATE_URL") == "localhost":
            client = weaviate.connect_to_local()
        else:
            client = weaviate.connect_to_custom(
                http_host=os.getenv("COP_WEAVIATE_URL"),
                http_port=8080,
                http_secure=False,
                grpc_host=os.getenv("COP_WEAVIATE_URL"),
                grpc_port=50051,
                grpc_secure=False,
                auth_credentials=weaviate.auth.AuthApiKey(
                    api_key=os.getenv("WEAVIATE_API_KEY"),
                ),
            )
    except Exception as e:
        error_message = "Failed to initialize Weaviate client"
        raise WeaviateClientInitializationError(error_message) from e
    else:
        return client


def extract_date_from_filename(filename: str) -> Optional[datetime]:
    """Extract date from filename pattern il_manifesto_del_D_MONTH_YYYY_cover.jpg."""
    try:
        month_map = {
            "gennaio": "01", "febbraio": "02", "marzo": "03", "aprile": "04",
            "maggio": "05", "giugno": "06", "luglio": "07", "agosto": "08",
            "settembre": "09", "ottobre": "10", "novembre": "11", "dicembre": "12",
        }

        date_part = filename.split("_del_")[1].split("_cover")[0]
        day, month_name, year = date_part.split("_")
        month = month_map[month_name.lower()]
        day = day.zfill(2)

        # Create a timezone-aware datetime directly
        return datetime(
            year=int(year),
            month=int(month),
            day=int(day),
            tzinfo=timezone.utc,
        )
    except Exception:
        return None
