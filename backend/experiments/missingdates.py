import os
import weaviate
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
)
logger = logging.getLogger(__name__)

def init_weaviate_client():
    """Initializes and returns a Weaviate client."""
    secrets_path = Path(__file__).parent.parent / '.secrets'
    load_dotenv(dotenv_path=secrets_path)
    
    weaviate_url = os.getenv("COP_WEAVIATE_URL", "")
    weaviate_api_key = os.getenv("COP_WEAVIATE_API_KEY", "")

    if not weaviate_url:
        raise ValueError("COP_WEAVIATE_URL environment variable not set.")

    if weaviate_url in ["localhost", "127.0.0.1"]:
        return weaviate.connect_to_local()
    
    return weaviate.connect_to_wcs(
        cluster_url=weaviate_url,
        auth_credentials=weaviate.auth.AuthApiKey(weaviate_api_key),
    )

def get_all_dates_from_weaviate(client, collection_name):
    """Fetches all edition dates from the specified Weaviate collection."""
    try:
        collection = client.collections.get(collection_name)
        
        response = collection.query.fetch_objects(
            limit=10000, # Adjust limit as needed
            return_properties=["editionId"]
        )
        
        dates = set()
        for obj in response.objects:
            try:
                date_str = obj.properties["editionId"]
                dates.add(datetime.strptime(date_str, "%d-%m-%Y").date())
            except (ValueError, KeyError) as e:
                logger.warning(f"Skipping invalid date format or missing 'editionId': {obj.properties}. Error: {e}")
        return dates
    except Exception as e:
        logger.exception(f"Failed to fetch dates from Weaviate collection '{collection_name}': {e}")
        return set()

def find_missing_dates(existing_dates, ignored_dates_str):
    """
    Finds missing dates between the oldest existing date and today,
    excluding Mondays and a list of specified holidays.
    """
    if not existing_dates:
        logger.warning("No existing dates found. Cannot determine date range.")
        return []

    oldest_date = min(existing_dates)
    today = datetime.now().date()
    
    # Parse ignored dates from DD/MM format to (day, month) tuples
    ignored_dates = set()
    for date_str in ignored_dates_str:
        try:
            day, month = map(int, date_str.split('/'))
            ignored_dates.add((day, month))
        except ValueError:
            logger.warning(f"Invalid format for ignored date '{date_str}'. Should be DD/MM.")

    missing_dates = []
    current_date = oldest_date
    while current_date <= today:
        # Monday is weekday 1 in isoweekday()
        if current_date.isoweekday() != 1:
            if (current_date.day, current_date.month) not in ignored_dates:
                if current_date not in existing_dates:
                    missing_dates.append(current_date)
        current_date += timedelta(days=1)
        
    return missing_dates

def main():
    """
    Main function to identify and report missing dates in the Weaviate collection.
    """
    try:
        client = init_weaviate_client()
        collection_name = os.getenv("COP_COPERTINE_COLLNAME", "Copertine")
        
        # List of dates to ignore in DD/MM format
        # Can be extended as needed
        ignored_holidays = ["16/08", "01/01", "02/05", "25/12", "26/12"]
        
        logger.info(f"Fetching existing dates from '{collection_name}' collection...")
        existing_dates = get_all_dates_from_weaviate(client, collection_name)
        
        if existing_dates:
            logger.info(f"Found {len(existing_dates)} existing dates.")
            logger.info(f"Oldest date in collection: {min(existing_dates).strftime('%d-%m-%Y')}")
            
            missing_dates = find_missing_dates(existing_dates, ignored_holidays)
            
            if missing_dates:
                logger.warning(f"Found {len(missing_dates)} missing dates (excluding Mondays and holidays):")
                for date in sorted(missing_dates):
                    print(date.strftime("%Y-%m-%d"))
            else:
                logger.info("No missing dates found. The collection is up-to-date.")
        else:
            logger.error("Could not retrieve any dates from Weaviate.")
            
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        if 'client' in locals() and client.is_connected():
            client.close()

if __name__ == "__main__":
    main()
