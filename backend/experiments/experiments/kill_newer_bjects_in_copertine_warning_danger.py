import argparse
import logging
import os
import sys
from datetime import datetime
from typing import Any

import weaviate
from dotenv import load_dotenv
from weaviate.classes.query import Filter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Italian month names mapping
TWO_DIGIT_YEAR_LENGTH = 2
ITALIAN_MONTHS = {
    'gen': '01', 'gennaio': '01',
    'feb': '02', 'febbraio': '02',
    'mar': '03', 'marzo': '03',
    'apr': '04', 'aprile': '04',
    'mag': '05', 'maggio': '05',
    'giu': '06', 'giugno': '06',
    'lug': '07', 'luglio': '07',
    'ago': '08', 'agosto': '08',
    'set': '09', 'settembre': '09',
    'ott': '10', 'ottobre': '10',
    'nov': '11', 'novembre': '11',
    'dic': '12', 'dicembre': '12'
}

def parse_date(date_str: str) -> str:
    """Parse date string and return in YYYY-MM-DD format."""
    def _try_parse_italian(date_str: str) -> str:
        """Try to parse Italian format like '20-gen-25' or '20-gen-2025'."""
        try:
            day, month, year = date_str.lower().split('-')
            if month in ITALIAN_MONTHS:
                month_num = ITALIAN_MONTHS[month]
                # Handle 2-digit years
                if len(year) == TWO_DIGIT_YEAR_LENGTH:
                    year = '20' + year  # Assume 20xx for years 00-99
                return f"{year}-{month_num}-{day.zfill(2)}"
        except (ValueError, KeyError):
            pass
        raise ValueError

    def _try_parse_standard(date_str: str) -> str:
        """Try standard date formats including 2-digit years."""
        for fmt in ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%y", "%d/%m/%y"]:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                continue
        raise ValueError

    try:
        # Try Italian format first, then standard formats
        try:
            return _try_parse_italian(date_str)
        except ValueError:
            return _try_parse_standard(date_str)
    except ValueError:
        logger.exception("Failed to parse date. Supported formats: DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD, YYYY/MM/DD, or DD-MMM-YYYY (Italian months)")
        sys.exit(1)

def init_weaviate_client() -> weaviate.WeaviateClient:
    """Initialize Weaviate client."""
    try:
        weaviate_url = os.getenv("COP_WEAVIATE_URL", "")
        if weaviate_url in ["localhost", "127.0.0.1"]:
            return weaviate.connect_to_local()

        return weaviate.connect_to_wcs(
            cluster_url=os.getenv("COP_WEAVIATE_URL"),
            auth_credentials=weaviate.auth.AuthApiKey(os.getenv("COP_WEAVIATE_API_KEY")),
        )
    except Exception:
        logger.exception("Failed to initialize Weaviate client")
        sys.exit(1)

def get_collection(client: weaviate.WeaviateClient) -> Any:
    """Get the Copertine collection."""
    try:
        cop_copertine_collname = os.getenv("COP_COPERTINE_COLLNAME")
        if not cop_copertine_collname:
            logger.error("COP_COPERTINE_COLLNAME environment variable not set")
            sys.exit(1)
        return client.collections.get(cop_copertine_collname)
    except Exception:
        logger.exception("Failed to get collection")
        sys.exit(1)

def count_and_delete_objects(collection: Any, date_str: str) -> None:
    """Count objects newer than given date and optionally delete them."""
    try:
        # Query objects with date filter
        result = collection.query.fetch_objects(
            filters=Filter.by_property("editionDateIsoStr").greater_than(f"{date_str}T00:00:00Z"),
            limit=1000,  # Adjust if needed
        )

        if not result.objects:
            logger.info("No objects found after date %s", date_str)
            return

        count = len(result.objects)
        logger.info("Found %d objects after date %s", count, date_str)

        # Ask for confirmation
        response = input(f"\nDo you want to delete these {count} objects? (yes/no): ").lower()
        if response != "yes":
            logger.info("Operation cancelled")
            return

        # Delete objects
        logger.warning("Deleting %d objects...", count)
        for obj in result.objects:
            collection.data.delete_by_id(obj.uuid)
        logger.info("Successfully deleted %d objects", count)

    except Exception:
        logger.exception("Error processing objects")
        sys.exit(1)

def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="Delete Weaviate objects newer than specified date")
    parser.add_argument(
        "date",
        help="Date in DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD, YYYY/MM/DD, or Italian format (e.g., 20-gen-2025)",
    )
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Parse and validate date
    date_str = parse_date(args.date)
    logger.info("Using date: %s", date_str)

    # Initialize Weaviate client
    client = init_weaviate_client()
    try:
        collection = get_collection(client)
        count_and_delete_objects(collection, date_str)
    finally:
        client.close()

if __name__ == "__main__":
    main()
