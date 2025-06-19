import logging
import os
from datetime import datetime, timezone

import weaviate
from dotenv import load_dotenv


class WeaviateClientInitializationError(Exception):
    """Custom exception for Weaviate client initialization errors."""


def setup_logging(name: str) -> logging.Logger:
    """Configure and return a logger."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
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
        weaviate_url = os.getenv("COP_WEAVIATE_URL", "")
        
        # Determine if this is a local connection (not a WCS URL)
        # WCS URLs typically start with https:// and contain weaviate cloud domains
        is_wcs = weaviate_url.startswith("https://") and (".weaviate." in weaviate_url or "weaviate.io" in weaviate_url)
        
        if not is_wcs:
            # This is a local connection
            if weaviate_url == "localhost":
                # Simple localhost case
                client = weaviate.connect_to_local()
            else:
                # Parse URL to extract host and port for local connections
                if "://" in weaviate_url:
                    # Parse full URL like http://weaviate2025:8090 or http://localhost:8080
                    protocol, rest = weaviate_url.split("://", 1)
                    if ":" in rest:
                        host, port_str = rest.split(":", 1)
                        port = int(port_str)
                    else:
                        host = rest
                        port = 8080
                else:
                    # Just hostname like "weaviate2025"
                    host = weaviate_url
                    port = 8080
                
                client = weaviate.connect_to_custom(
                    http_host=host,
                    http_port=port,
                    http_secure=False,
                    grpc_host=host,
                    grpc_port=50051,
                    grpc_secure=False,
                )
        else:
            # For remote WCS connections
            weaviate_api_key = os.getenv("COP_WEAVIATE_API_KEY", "")
            client = weaviate.connect_to_wcs(
                cluster_url=weaviate_url,
                auth_credentials=weaviate.auth.AuthApiKey(weaviate_api_key),
            )
    except Exception as e:
        error_message = "Failed to initialize Weaviate client"
        raise WeaviateClientInitializationError(error_message) from e
    else:
        return client


def extract_date_from_filename(filename: str) -> datetime | None:
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
