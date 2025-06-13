import argparse

import logging
import os

import sys

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import weaviate

from dotenv import load_dotenv
from weaviate.classes.query import Filter
from weaviate.collections.classes.filters import Filter as FilterV4

from includes.weschema import COPERTINE_COLL_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.FileHandler("scrapedirectus.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Constants
HTTP_STATUS_OK = 200
SEPARATOR_LINE = "-" * 50
MISSING_IMAGES_DIR_MSG = "COP_IMAGES_DIR environment variable must be set"

class DirectusManifestoScraper:
    def __init__(self):
        self.client = None
        self.collection = None
        # Load environment variables
        load_dotenv()
        # Initialize Weaviate client
        self.client = self._init_weaviate_client()
        self.collection = self._ensure_collection()
        # Get images directory from environment
        images_dir_str = os.getenv("COP_IMAGES_DIR")
        if not images_dir_str:
            raise ValueError(MISSING_IMAGES_DIR_MSG)
        self.images_dir = Path(images_dir_str)
        # Create images directory
        self.images_dir.mkdir(parents=True, exist_ok=True)
        # Directus config
        self.directus_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {os.getenv("DIRECTUS_API_TOKEN")}'
        }
        self.directus_url = "https://directus.ilmanifesto.it/items/articles"
        self.assets_url = "https://directus.ilmanifesto.it/assets"

    def _init_weaviate_client(self) -> weaviate.WeaviateClient:
        """Initialize Weaviate client with error handling"""
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
            raise

    def _ensure_collection(self):
        """Ensure the Copertine collection exists in Weaviate"""
        cop_copertine_collname = os.getenv("COP_COPERTINE_COLLNAME")
        collection = None

        try:
            collections = self.client.collections.list_all()
            if cop_copertine_collname not in collections:
                collection = self.client.collections.create_from_dict(COPERTINE_COLL_CONFIG)
                logger.info("Created %s collection in Weaviate", cop_copertine_collname)
            else:
                collection = self.client.collections.get(cop_copertine_collname)
        except Exception:
            logger.exception("Failed to create or get collection: %s", cop_copertine_collname)
            raise

        return collection

    def get_asset_url(self, image_id):
        try:
            image_record_url = f"https://directus.ilmanifesto.it/items/images/{image_id}"
            response = httpx.get(image_record_url, headers=self.directus_headers)
            response.raise_for_status()
            image_record = response.json().get('data')
            if image_record is None:
                logging.error(str(image_id) + " no image record found")
                return None
            if "image" in image_record:
                return self.assets_url + '/' + image_record["image"]
            else:
                logging.error("Error: malformed image record")
                return None
        except httpx.RequestError:
            logger.exception("Error getting asset url for image %s", image_id)
            return None

    def download_directus_image(self, client: httpx.Client, image_url: str, filename: Path) -> bool:
        """Download image from URL and save to file"""
        try:
            logger.info("Attempting to download image from: %s", image_url)
            response = client.get(image_url, headers=self.directus_headers)
            response.raise_for_status()
        except httpx.RequestError:
            logger.exception("Error downloading image %s", image_url)
            return False
        else:
            if response.status_code == HTTP_STATUS_OK:
                try:
                    abs_path = filename.resolve()
                    abs_path.parent.mkdir(parents=True, exist_ok=True)
                    abs_path.write_bytes(response.content)
                    logger.info("Image saved successfully to %s. Size: %d bytes", abs_path, len(response.content))
                    return True
                except Exception:
                    logger.exception("Error saving image to %s", abs_path)
                    return False
            logger.warning("Failed to download image. Status code: %d", response.status_code)
            return False

    def transform_image_url_to_filename(self, image_url: str, date_str: str) -> str:
        """Transform CDN URL to filename"""
        try:
            image_path = image_url.split('/')[-1]
            date_parts = date_str.split("-")
            formatted_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"
            return f"il-manifesto_{formatted_date}_{image_path}"
        except Exception:
            return ""

    def store_in_weaviate(self, article: dict[str, Any], image_filename: str):
        """Store scraped data in Weaviate"""
        try:
            date_published = datetime.fromisoformat(article['datePublished'])
            date_str = date_published.strftime("%d-%m-%Y")
            iso_date = date_published.isoformat()

            data = {
                "testataName": "Il Manifesto",
                "editionId": article.get("articleEdition", date_str),
                "editionDateIsoStr": iso_date,
                "editionImageFnStr": image_filename,
                "captionStr": article.get("referenceHeadline"),
                "kickerStr": article.get("articleKicker"),
            }

            self.collection.data.insert(data)
            logger.info("Successfully stored data in Weaviate for date %s", date_str)
        except Exception:
            logger.exception("Failed to store data in Weaviate for article %s", article.get('id'))

    def _delete_existing_edition(self, edition_id: str):
        """Delete existing edition from Weaviate if it exists"""
        try:
            result = self.collection.query.fetch_objects(
                filters=FilterV4.by_property("editionId").equal(edition_id)
            )
            for obj in result.objects:
                self.collection.data.delete_by_id(obj.uuid)
            if result.objects:
                logger.info("Deleted %d existing editions for editionId %s", len(result.objects), edition_id)
        except Exception:
            logger.exception("Failed to delete existing edition in Weaviate for editionId %s", edition_id)

    def fetch_directus_articles(self, params: dict, replace_mode: bool):
        client = httpx.Client(timeout=30.0, follow_redirects=True)
        try:
            response = client.get(self.directus_url, params=params, headers=self.directus_headers)
            response.raise_for_status()
            articles = response.json().get('data', [])
            logger.info(f"Retrieved {len(articles)} articles from Directus.")

            for article in articles:
                if replace_mode:
                    self._delete_existing_edition(article['articleEdition'])

                image_id = article.get('articleFeaturedImage')
                if not image_id:
                    logger.warning(f"Article {article['id']} has no featured image. Skipping.")
                    continue

                image_url = self.get_asset_url(image_id)
                if not image_url:
                    logger.warning(f"Could not get asset URL for image {image_id}. Skipping article {article['id']}.")
                    continue

                date_published = datetime.fromisoformat(article['datePublished'])
                date_str = date_published.strftime("%d-%m-%Y")
                image_filename = self.transform_image_url_to_filename(image_url, date_str)

                if image_filename:
                    image_path = self.images_dir / image_filename
                    if self.download_directus_image(client, image_url, image_path):
                        self.store_in_weaviate(article, image_filename)
                    else:
                        logger.error(f"Failed to download image for article {article['id']}. Skipping.")
                else:
                    logger.error(f"Failed to generate image filename for article {article['id']}. Skipping.")
        finally:
            client.close()

    def cleanup(self):
        """Explicit cleanup method to ensure resources are properly released"""
        if hasattr(self, 'client') and self.client:
            try:
                self.client.close()
            except Exception:
                logger.exception("Error while closing Weaviate client")
            finally:
                self.client = None
                self.collection = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Fetch Il Manifesto copertina articles from Directus CMS and store in Weaviate"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '-n', '--number',
        type=int,
        help='Number of days to fetch starting from today (e.g., -n 7 for last 7 days)'
    )
    group.add_argument(
        '--date',
        type=str,
        help='Specific date to fetch in YYYY-MM-DD format (replaces existing data)'
    )
    return parser.parse_args()

def calculate_date_range(args):
    today = datetime.now(tz=timezone.utc)
    if args.number:
        end_date = today
        start_date = today - timedelta(days=args.number -1)
        replace_mode = False
    elif args.date:
        try:
            target_date = datetime.strptime(f"{args.date} +0000", "%Y-%m-%d %z")
            start_date = end_date = target_date
            replace_mode = True
        except ValueError:
            raise ValueError("Invalid date format. Expected YYYY-MM-DD")
    return start_date, end_date, replace_mode

def build_directus_params(start_date, end_date):
    params = {
        'fields': 'id,articleEdition,referenceHeadline,articleTag,articleKicker,datePublished,author,headline,articleEditionPosition,articleFeaturedImageDescription,articleFeaturedImage',
        'filter[syncSource][_eq]': 'wp',
        'filter[articleEditionPosition][_eq]': 1,
        'filter[articleFeaturedImage][_nnull]': True,
        'filter[referenceHeadline][_nnull]': True,
        'sort': '-datePublished',
        'limit': -1 # Fetch all matching
    }
    # Format dates to be compatible with Directus (_gte, _lte)
    params['filter[datePublished][_gte]'] = start_date.strftime('%Y-%m-%dT00:00:00')
    params['filter[datePublished][_lte]'] = end_date.strftime('%Y-%m-%dT23:59:59')
    return params

def main():
    args = parse_arguments()
    try:
        start_date, end_date, replace_mode = calculate_date_range(args)
        logger.info(f"Fetching articles from {start_date.date()} to {end_date.date()}")
        if replace_mode:
            logger.warning("Replace mode enabled: existing data for the specified date will be overwritten.")

        with DirectusManifestoScraper() as scraper:
            params = build_directus_params(start_date, end_date)
            scraper.fetch_directus_articles(params, replace_mode)
        logger.info("Successfully completed article fetching.")
    except Exception:
        logger.exception("Application failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
