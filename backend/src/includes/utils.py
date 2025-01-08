# utils.py
from datetime import datetime
import logging
import os
from typing import Optional

from dotenv import load_dotenv
import weaviate


def setup_logging(name: str) -> logging.Logger:
    """Configure and return a logger"""
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
    """Initialize Weaviate client with error handling"""
    load_dotenv()
    try:
        if os.getenv("COP_WEAVIATE_URL") == "localhost":
            client = weaviate.connect_to_local()
        else:
            client = weaviate.connect(
                connection_params=weaviate.auth.AuthApiKey(
                    api_key=os.getenv("WEAVIATE_API_KEY"),
                ),
                host=os.getenv("COP_WEAVIATE_URL"),
            )
        return client
    except Exception as e:
        raise Exception(f"Failed to initialize Weaviate client: {e!s}")

def extract_date_from_filename(filename: str) -> Optional[datetime]:
    """Extract date from filename pattern il_manifesto_del_D_MONTH_YYYY_cover.jpg"""
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

        date_str = f"{year}-{month}-{day}"
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return None
