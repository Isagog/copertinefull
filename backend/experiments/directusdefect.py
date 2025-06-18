import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
#     handlers=[
#         logging.StreamHandler(),
#     ],
# )
# logger = logging.getLogger(__name__)

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Check for missing properties in Directus articles for a list of dates."
    )
    parser.add_argument(
        '--datefile',
        type=str,
        required=True,
        help='File containing a list of dates to check, one per line in YYYY-MM-DD format'
    )
    return parser.parse_args()

def build_directus_params(start_date, end_date):
    params = {
        'fields': 'id,datePublished,referenceHeadline,articleFeaturedImage,articleKicker',
        'filter[syncSource][_eq]': 'wp',
        'filter[articleEditionPosition][_eq]': 1,
        'sort': '-datePublished',
        'limit': 1
    }
    params['filter[datePublished][_gte]'] = start_date.strftime('%Y-%m-%dT00:00:00')
    params['filter[datePublished][_lte]'] = end_date.strftime('%Y-%m-%dT23:59:59')
    return params

def check_article_properties(article):
    required_properties = [
        "datePublished",
        "articleFeaturedImage",
        "referenceHeadline",
    ]
    optional_properties = [
        "id",
        "articleKicker",
    ]
    missing_required = []
    missing_optional = []
    
    for prop in required_properties:
        if not article.get(prop):
            missing_required.append(prop)
            
    for prop in optional_properties:
        if not article.get(prop):
            missing_optional.append(prop)
            
    return missing_required, missing_optional

def process_date(date_str, directus_url, directus_headers):
    try:
        target_date = datetime.strptime(f"{date_str} +0000", "%Y-%m-%d %z")
        start_date = end_date = target_date
    except ValueError:
        print(f"{date_str} - Invalid date format. Expected YYYY-MM-DD.")
        return

    params = build_directus_params(start_date, end_date)
    
    try:
        with httpx.Client() as client:
            response = client.get(directus_url, params=params, headers=directus_headers)
            response.raise_for_status()
            articles = response.json().get('data', [])

            if not articles:
                print(f"{date_str} - No article found for this date.")
                return

            article = articles[0]
            print(f"{date_str} - Article found with ID: {article.get('id')}")
            
            missing_required, missing_optional = check_article_properties(article)
            
            for prop in missing_required:
                print(f"\tERROR - Missing required property: {prop}")
            
            for prop in missing_optional:
                print(f"\tWARNING - Missing property: {prop}")

    except httpx.HTTPStatusError as e:
        print(f"{date_str} - HTTP error occurred: {e}", file=sys.stderr)
    except Exception as e:
        print(f"{date_str} - An unexpected error occurred: {e}", file=sys.stderr)

def main():
    args = parse_arguments()
    
    secrets_path = Path(__file__).parent.parent / '.secrets'
    load_dotenv(dotenv_path=secrets_path)
    
    directus_token = os.getenv("DIRECTUS_API_TOKEN")
    if not directus_token:
        print("ERROR: DIRECTUS_API_TOKEN not found in .secrets file.", file=sys.stderr)
        sys.exit(1)

    directus_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {directus_token}'
    }
    directus_url = "https://directus.ilmanifesto.it/items/articles"

    date_file = Path(args.datefile)
    if not date_file.is_file():
        print(f"ERROR: Date file not found: {args.datefile}", file=sys.stderr)
        sys.exit(1)

    with date_file.open('r') as f:
        for line in f:
            date_str = line.strip()
            if not date_str:
                continue
            process_date(date_str, directus_url, directus_headers)

if __name__ == "__main__":
    main()
