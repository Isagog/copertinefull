import argparse
import logging
import os
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class InvalidDateFormatError(ValueError):
    """Custom exception for invalid date formats."""

    def __init__(self, message="Invalid date format. Expected YYYY-MM-DD"):
        self.message = message
        super().__init__(self.message)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Debug script to fetch articles from Directus CMS."
    )
    parser.add_argument(
        '--date',
        type=str,
        required=True,
        help='Specific date to fetch in YYYY-MM-DD format'
    )
    return parser.parse_args()

def calculate_date_range(args):
    try:
        target_date = datetime.strptime(f"{args.date} +0000", "%Y-%m-%d %z")
        start_date = end_date = target_date
    except ValueError as e:
        raise InvalidDateFormatError() from e
    return start_date, end_date

def build_directus_params(start_date, end_date):
    params = {
        'fields': 'id,articleEdition,referenceHeadline,articleTag,articleKicker,datePublished,author,headline,articleEditionPosition,articleFeaturedImageDescription,articleFeaturedImage',
        'filter[datePublished][_gte]': start_date.strftime('%Y-%m-%dT00:00:00'),
        'filter[datePublished][_lte]': end_date.strftime('%Y-%m-%dT23:59:59'),
        'sort': '-datePublished',
        'limit': -1 
    }
    
    # TO DEBUG: Comment out or modify these filters to see what data is returned
    params['filter[syncSource][_eq]'] = 'wp'
    params['filter[articleEditionPosition][_eq]'] = 1
    params['filter[articleFeaturedImage][_nnull]'] = True
    params['filter[referenceHeadline][_nnull]'] = True
    
    return params

def main():
    args = parse_arguments()
    
    # Load environment variables from .secrets file
    secrets_path = Path(__file__).parent.parent / '.secrets'
    load_dotenv(dotenv_path=secrets_path)
    
    directus_api_token = os.getenv("DIRECTUS_API_TOKEN")
    if not directus_api_token:
        logger.error("DIRECTUS_API_TOKEN not found in .secrets file.")
        return

    directus_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {directus_api_token}'
    }
    directus_url = "https://directus.ilmanifesto.it/items/articles"

    try:
        start_date, end_date = calculate_date_range(args)
        logger.info(f"Fetching articles from {start_date.date()} to {end_date.date()}")

        params = build_directus_params(start_date, end_date)
        
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(directus_url, params=params, headers=directus_headers)
            response.raise_for_status()
            articles = response.json().get('data', [])
            
            logger.info(f"Retrieved {len(articles)} articles from Directus.")
            
            if articles:
                logger.info("Found articles:")
                for article in articles:
                    logger.info(f"  - ID: {article.get('id')}, Headline: {article.get('referenceHeadline')}, Position: {article.get('articleEditionPosition')}")
            else:
                logger.info("No articles found matching the criteria.")

    except Exception:
        logger.exception("An error occurred during the process.")

if __name__ == "__main__":
    main()
