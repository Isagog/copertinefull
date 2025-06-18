import argparse
import logging
import mimetypes
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

import httpx
import weaviate
from dotenv import load_dotenv
from weaviate.classes.query import Filter
from weaviate.util import generate_uuid5

from includes.weschema import COPERTINE_COLL_CONFIG


class MissingEnvironmentVariableError(ValueError):
    """Custom exception for missing environment variables."""

    def __init__(self, var_name: str):
        self.var_name = var_name
        super().__init__()

    def __str__(self):
        return f"Environment variable '{self.var_name}' must be set."


class InvalidDateFormatError(ValueError):
    """Custom exception for invalid date formats."""

    def __init__(self, date_str: str):
        self.date_str = date_str
        super().__init__()

    def __str__(self):
        return f"Invalid date format for '{self.date_str}'"


def _get_required_env(var_name: str) -> str:
    """Get a required environment variable or raise an error."""
    value = os.getenv(var_name)
    if value is None:
        raise MissingEnvironmentVariableError(var_name)
    return value


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.FileHandler("scrapedirectus.log"),
        logging.StreamHandler(),
    ],
)
logging.getLogger("weaviate").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
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
        secrets_path = Path(__file__).parent.parent / '.secrets'
        load_dotenv(dotenv_path=secrets_path, override=True)
        # Initialize Weaviate client
        self.client = self._init_weaviate_client()
        self.collection = self._ensure_collection()
        # Set images directory
        self.images_dir = Path(__file__).parent.parent.parent / "images"
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
            weaviate_url = _get_required_env("COP_WEAVIATE_URL")
            weaviate_api_key = os.getenv("COP_WEAVIATE_API_KEY")

            if "localhost" in weaviate_url or "127.0.0.1" in weaviate_url:
                parsed_url = urlparse(weaviate_url)
                return weaviate.connect_to_local(
                    host=parsed_url.hostname,
                    port=parsed_url.port,
                )
            
            # Default to WCS connection for other URLs
            return weaviate.connect_to_wcs(
                cluster_url=weaviate_url,
                auth_credentials=weaviate.auth.AuthApiKey(weaviate_api_key),
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
                logging.error("    %s no image record found", image_id)
                return None
            if "image" in image_record:
                return self.assets_url + '/' + image_record["image"]
            else:
                logging.error("    Error: malformed image record")
                return None
        except httpx.RequestError:
            logger.exception("    Error getting asset url for image %s", image_id)
            return None

    def download_directus_image(self, client: httpx.Client, image_url: str, filename: Path) -> str | None:
        """Download image from URL and save to file"""
        try:
            logger.info("    Attempting to download image from: %s", image_url)
            response = client.get(image_url, headers=self.directus_headers)
            response.raise_for_status()
        except httpx.RequestError:
            logger.exception("    Error downloading image %s", image_url)
            return None
        else:
            if response.status_code == HTTP_STATUS_OK:
                content_type = response.headers.get('content-type')
                if not content_type:
                    logger.warning("    No content-type header found for image %s", image_url)
                    return None

                extension = mimetypes.guess_extension(content_type)
                if not extension:
                    logger.warning("    Could not determine file extension for content-type %s", content_type)
                    # Fallback to a common extension like .jpg if needed, or handle as an error
                    extension = '.jpg' # Example fallback

                # Append the extension to the filename
                new_filename_with_ext = filename.with_suffix(extension)
                
                try:
                    abs_path = new_filename_with_ext.resolve()
                    abs_path.parent.mkdir(parents=True, exist_ok=True)
                    abs_path.write_bytes(response.content)
                except Exception:
                    logger.exception("    Error saving image to %s", abs_path)
                    return None
                else:
                    logger.info("    Image saved successfully to %s. Size: %d bytes", abs_path, len(response.content))
                    return new_filename_with_ext.name
            logger.warning("    Failed to download image. Status code: %d", response.status_code)
            return None

    def slugify(self, text: str) -> str:
        """Convert string to a URL-friendly slug."""
        text = text.lower()
        text = re.sub(r'[\s\W]+', '-', text)  # Replace spaces and non-alphanumeric chars with -
        return text.strip('-')

    def transform_image_url_to_filename(self, article: dict[str, Any], date_str: str) -> str:
        """Generate a descriptive filename from the article's reference headline."""
        try:
            headline = article.get("referenceHeadline", "")
            if not headline:
                # Fallback to image ID if headline is not available
                image_url = self.get_asset_url(article.get('articleFeaturedImage'))
                if image_url:
                    return image_url.split('/')[-1]
                return ""

            slug = self.slugify(headline)
            date_parts = date_str.split("-")
            formatted_date = f"{date_parts[0]}-{date_parts[1]}-{date_parts[2]}"  # YYYY-MM-DD
        except Exception:
            logger.exception("Error transforming image URL to filename")
            return ""
        else:
            return f"il-manifesto_{formatted_date}_{slug}"

    def store_in_weaviate(self, article: dict[str, Any], image_filename: str):
        """Store scraped data in Weaviate, overwriting if it already exists."""
        try:
            date_published = datetime.fromisoformat(article["datePublished"])
            edition_id = date_published.strftime("%d-%m-%Y")
            iso_date = date_published.isoformat()

            # Generate a deterministic UUID based on the editionId
            # The namespace UUID is arbitrary, but must be constant.
            # Using the UUID of the string "ilmanifesto.it" as a namespace.
            namespace_uuid = UUID("c1e7c19c-2c4c-5c9c-9c9c-c1e7c19c2c4c")
            uuid = generate_uuid5(edition_id, namespace_uuid)

            data = {
                "testataName": "Il Manifesto",
                "editionId": edition_id,
                "editionDateIsoStr": iso_date,
                "editionImageFnStr": image_filename,
                "captionStr": article.get("referenceHeadline"),
                "kickerStr": article.get("articleKicker"),
            }

            try:
                self.collection.data.insert(properties=data, uuid=uuid)
                logger.info(
                    "    Successfully stored data in Weaviate for date %s with UUID %s",
                    edition_id,
                    uuid,
                )
            except weaviate.exceptions.UnexpectedStatusCodeError as e:
                if "already exists" in str(e):
                    self.collection.data.replace(properties=data, uuid=uuid)
                    logger.info(
                        "    Successfully updated data in Weaviate for date %s with UUID %s",
                        edition_id,
                        uuid,
                    )
                else:
                    raise
        except Exception:
            logger.exception(
                "    Failed to store data in Weaviate for article %s", article.get("id")
            )

    def _validate_article(self, article: dict) -> bool:
        """Validate that an article has all the required properties."""
        article_id = article.get("id", "N/A")
        has_errors = False
        required_fields = ["referenceHeadline", "articleFeaturedImage"]
        for field in required_fields:
            if not article.get(field):
                logger.error(f"    Article {article_id}: Missing required property: {field}")
                has_errors = True

        optional_fields = ["articleKicker"]
        for field in optional_fields:
            if not article.get(field):
                logger.warning(f"    Article {article_id}: Missing property: {field}")

        return not has_errors

    def _process_image(self, article: dict, client: httpx.Client, date_str: str):
        """Download and process the image for an article."""
        article_id = article.get("id", "N/A")
        image_id = article.get('articleFeaturedImage')

        image_url = self.get_asset_url(image_id)
        if not image_url:
            logger.warning(f"    Could not get asset URL for image {image_id}. Skipping article {article_id}.")
            return

        image_filename = self.transform_image_url_to_filename(article, date_str)
        if not image_filename:
            logger.error(f"    Failed to generate image filename for article {article_id}. Skipping.")
            return

        image_path = self.images_dir / image_filename
        final_image_filename = self.download_directus_image(client, image_url, image_path)
        if final_image_filename:
            self.store_in_weaviate(article, final_image_filename)
        else:
            logger.error(f"    Failed to download image for article {article_id}. Skipping.")

    def _process_article(self, article: dict, client: httpx.Client, processed_edition_ids: set, is_single_date: bool):
        date_published = datetime.fromisoformat(article['datePublished'])
        date_str = date_published.strftime("%Y-%m-%d")
        if not is_single_date:
            logger.info(f"Fetching article for date: {date_str}")

        if not self._validate_article(article):
            logger.info(f"    Skipping article {article.get('id', 'N/A')} due to missing required properties.")
            return

        edition_id = date_published.strftime("%d-%m-%Y")
        if edition_id in processed_edition_ids:
            logger.info(f"    Already processed edition {edition_id}, skipping article {article.get('id', 'N/A')}.")
            return
        processed_edition_ids.add(edition_id)

        self._process_image(article, client, date_str)

    def fetch_directus_articles(self, params: dict, is_single_date: bool = False):
        client = httpx.Client(timeout=30.0, follow_redirects=True)
        processed_edition_ids = set()
        try:
            response = client.get(self.directus_url, params=params, headers=self.directus_headers)
            response.raise_for_status()
            articles = response.json().get('data', [])

            if is_single_date:
                if len(articles) == 0:
                    logger.info("    Retrieved 0 articles from Directus.")
                    return
            else:
                logger.info(f"Retrieved {len(articles)} articles from Directus.")

            for article in articles:
                self._process_article(article, client, processed_edition_ids, is_single_date)
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
        help='Specific date to fetch in YYYY-MM-DD format'
    )
    group.add_argument(
        '--datefile',
        type=str,
        help='File containing a list of dates to fetch, one per line in YYYY-MM-DD format'
    )
    return parser.parse_args()

def calculate_date_range(date_str=None, number=None):
    today = datetime.now(tz=timezone.utc)
    if number:
        end_date = today
        start_date = today - timedelta(days=number - 1)
    elif date_str:
        try:
            target_date = datetime.strptime(f"{date_str} +0000", "%Y-%m-%d %z")
            start_date = end_date = target_date
        except ValueError as e:
            raise InvalidDateFormatError(date_str) from e
    return start_date, end_date

def build_directus_params(start_date, end_date):
    params = {
        'fields': 'id,articleEdition,referenceHeadline,articleTag,articleKicker,datePublished,author,headline,articleEditionPosition,articleFeaturedImageDescription,articleFeaturedImage',
        'filter[syncSource][_eq]': 'wp',
        'filter[articlePositionCover][_eq]': 1,
        # 'filter[articleFeaturedImage][_nnull]': True,
        # 'filter[referenceHeadline][_nnull]': True,
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
        with DirectusManifestoScraper() as scraper:
            if args.datefile:
                date_file = Path(args.datefile)
                if not date_file.is_file():
                    logger.error(f"Date file not found: {args.datefile}")
                    sys.exit(1)
                
                with date_file.open('r') as f:
                    for line in f:
                        date_str = line.strip()
                        if not date_str:
                            continue
                        try:
                            start_date, end_date = calculate_date_range(date_str=date_str)
                            logger.info(f"Fetching article for date: {date_str}")
                            params = build_directus_params(start_date, end_date)
                            scraper.fetch_directus_articles(params, is_single_date=True)
                        except ValueError:
                            logger.exception()
                            continue
            else:
                start_date, end_date = calculate_date_range(date_str=args.date, number=args.number)
                params = build_directus_params(start_date, end_date)
                if args.date:
                    logger.info(f"Fetching article for date: {args.date}")
                    scraper.fetch_directus_articles(params, is_single_date=True)
                else:
                    logger.info(f"Fetching articles from {start_date.date()} to {end_date.date()}")
                    scraper.fetch_directus_articles(params)

        logger.info("Successfully completed article fetching.")
    except ValueError:
        logger.exception()
        sys.exit(1)
    except Exception:
        logger.exception("Application failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
