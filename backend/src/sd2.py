# Scrape Directus 2
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

import requests
import weaviate
import weaviate.classes as wvc
from weaviate.classes.init import Auth
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from includes.weschema import COPERTINE_COLL_CONFIG

# Constants
HTTP_OK = 200


class ScraperError(Exception):
    """Base exception for scraper errors."""
    pass


class MissingEnvironmentVariableError(ScraperError):
    """Exception for missing environment variables."""
    
    def __init__(self, var_name: str):
        self.var_name = var_name
        super().__init__(f"Environment variable '{var_name}' must be set.")


class InvalidDateFormatError(ScraperError):
    """Exception for invalid date formats."""
    
    def __init__(self, date_str: str):
        self.date_str = date_str
        super().__init__(f"Invalid date format for '{date_str}'. Expected YYYY-MM-DD format.")


class DateFileNotFoundError(ScraperError):
    """Exception for missing date files."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        super().__init__(f"Date file not found: {file_path}")

    
class WeaviateURLError(ValueError):
    """Custom exception for missing Weaviate URL."""
    def __init__(self, message="COP_WEAVIATE_URL environment variable not set."):
        self.message = message
        super().__init__(self.message)

class DirectusManifestoScraper:
    """Scraper for Il Manifesto copertina articles from Directus CMS."""
    
    def __init__(self):
        self._setup_logging()
        self._load_environment()
        self._init_weaviate()
        self._init_directus()
        self._setup_images_dir()
    
    def _setup_logging(self):
        """Configure logging."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
            handlers=[
                logging.FileHandler("scrapedirectus.log"),
                logging.StreamHandler(),
            ],
        )
        # Reduce noise from external libraries
        for lib in ["weaviate", "httpx", "httpcore"]:
            logging.getLogger(lib).setLevel(logging.WARNING)
        
        self.logger = logging.getLogger(__name__)
    
    def _load_environment(self):
        """Load environment variables."""
        secrets_path = Path(__file__).parent.parent / '.secrets'
        load_dotenv(dotenv_path=secrets_path, override=True)
    
    def _get_required_env(self, var_name: str) -> str:
        """Get a required environment variable or raise an error."""
        value = os.getenv(var_name)
        if value is None:
            raise MissingEnvironmentVariableError(var_name)
        return value

    
    def _init_weaviate(self):
        """Initialize Weaviate client and collection."""
        try:
            secrets_path = Path(__file__).parent.parent / ".secrets"
            load_dotenv(dotenv_path=secrets_path)

            weaviate_url = os.getenv("COP_WEAVIATE_URL", "")
            weaviate_api_key = os.getenv("COP_WEAVIATE_API_KEY", "")
            weaviate_grpc_port = os.getenv("COP_WEAVIATE_GRPC_PORT", "50051")

            if not weaviate_url:
                raise WeaviateURLError()

            # This is a local connection - extract host and port
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
                # Just hostname like "localhost" or "weaviate2025"
                host = weaviate_url
                port = 8080

            # Convert grpc_port to int
            grpc_port = int(weaviate_grpc_port)

            # Handle API key authentication for local connections
            if weaviate_api_key and weaviate_api_key.strip():
                self.weaviate_client = weaviate.connect_to_local(
                    host=host,
                    port=port,
                    grpc_port=grpc_port,
                    auth_credentials=Auth.api_key(weaviate_api_key),
                )
            else:
                self.weaviate_client = weaviate.connect_to_local(
                    host=host,
                    port=port,
                    grpc_port=grpc_port,
                )
            
            # Ensure collection exists only after successful connection
            self._ensure_collection()
            
            # Return the client to the caller
            return self.weaviate_client
            
        except Exception:
            self.logger.exception("Failed to initialize Weaviate client")
            raise
    
    def _ensure_collection(self):
        """Ensure the Copertine collection exists in Weaviate."""
        try:
            collection_name = self._get_required_env("COP_COPERTINE_COLLNAME")
            collections = self.weaviate_client.collections.list_all()
            
            if collection_name not in collections:
                self.collection = self.weaviate_client.collections.create_from_dict(COPERTINE_COLL_CONFIG)
                self.logger.info(f"Created {collection_name} collection in Weaviate")
            else:
                self.collection = self.weaviate_client.collections.get(collection_name)
                
        except Exception:
            self.logger.exception("Failed to create or get collection")
            raise
    
    def _init_directus(self):
        """Initialize Directus configuration."""
        self.directus_token = self._get_required_env("DIRECTUS_API_TOKEN")
        self.directus_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.directus_token}'
        }
        self.directus_url = "https://directus.ilmanifesto.it/items/articles"
        self.assets_url = "https://directus.ilmanifesto.it/assets"
    
    def _setup_images_dir(self):
        """Setup images directory."""
        self.images_dir = Path(__file__).parent.parent.parent / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
    
    def parse_dates_from_args(self) -> list[datetime]:
        """Parse command line arguments and return list of dates to process."""
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
        
        args = parser.parse_args()
        
        if args.number:
            return self._generate_date_range(args.number)
        elif args.date:
            return [self._parse_single_date(args.date)]
        elif args.datefile:
            return self._parse_date_file(args.datefile)
    
    def _generate_date_range(self, number_of_days: int) -> list[datetime]:
        """Generate a list of dates for the last N days."""
        today = datetime.now(tz=timezone.utc)
        dates = []
        for i in range(number_of_days):
            date = today - timedelta(days=i)
            dates.append(date)
        return dates
    
    def _parse_single_date(self, date_str: str) -> datetime:
        """Parse a single date string."""
        try:
            return datetime.strptime(f"{date_str} +0000", "%Y-%m-%d %z")
        except ValueError as e:
            raise InvalidDateFormatError(date_str) from e
    
    def _parse_date_file(self, date_file_path: str) -> list[datetime]:
        """Parse dates from a file."""
        date_file = Path(date_file_path)
        if not date_file.is_file():
            raise DateFileNotFoundError(date_file_path)
        
        dates = []
        with date_file.open('r') as f:
            for line_num, line in enumerate(f, 1):
                date_str = line.strip()
                if not date_str:
                    continue
                try:
                    dates.append(self._parse_single_date(date_str))
                except InvalidDateFormatError as e:
                    self.logger.warning(f"Line {line_num}: {e}")
                    continue
        return dates
    
    def process_copertine(self, dates: list[datetime]):
        """Process copertina articles for multiple dates."""
        self.logger.info(f"Processing {len(dates)} dates")
        
        for date in dates:
            date_str = date.strftime("%Y-%m-%d")
            self.logger.info(f"Processing copertina for date: {date_str}")
            
            try:
                article = self._fetch_copertina_for_date(date)
                if article:
                    self._process_copertina(article, date)
                else:
                    self.logger.error(f"No copertina found for date: {date_str}")
            except Exception:
                self.logger.exception(f"Failed to process copertina for {date_str}")
                continue
    
    def _fetch_copertina_for_date(self, date: datetime) -> dict[str, Any] | None:
        """Fetch copertina article for a specific date from Directus."""
        params = {
            'fields': 'id,articleEdition,referenceHeadline,articleTag,articleKicker,datePublished,author,headline,articleEditionPosition,articleFeaturedImageDescription,articleFeaturedImage',
            'filter[syncSource][_eq]': 'wp',
            'filter[articlePositionCover][_eq]': 1,
            'filter[datePublished][_gte]': date.strftime('%Y-%m-%dT00:00:00'),
            'filter[datePublished][_lte]': date.strftime('%Y-%m-%dT23:59:59'),
            'sort': '-datePublished',
            'limit': 1
        }
        
        try:
            response = requests.get(self.directus_url, params=params, headers=self.directus_headers, timeout=30.0)
            response.raise_for_status()
            
            articles = response.json().get('data', [])
            if articles:
                return articles[0]  # Return the first (and should be only) article
            return None
                
        except requests.RequestException:
            self.logger.exception(f"Error fetching copertina for {date.strftime('%Y-%m-%d')}")
            return None
    
    def _process_copertina(self, article: dict[str, Any], date: datetime):
        """Process a single copertina article."""
        if not self._validate_article(article):
            self.logger.warning(f"Article validation failed for ID {article.get('id')}")
            return
        
        # Generate edition_id in DD-MM-YYYY format
        edition_id = date.strftime("%d-%m-%Y")
        
        # Delete existing copertine with the same editionId
        deletion_successful = self._delete_existing_copertine(edition_id)
        if not deletion_successful:
            self.logger.error(f"Failed to delete existing objects with editionId {edition_id}. Aborting insertion to prevent duplicates.")
            return
        
        # Download image and store in Weaviate
        image_filename = self._download_and_save_image(article, date)
        if image_filename:
            self._store_in_weaviate(article, date, image_filename)
        else:
            self.logger.error(f"Failed to download image for article {article.get('id')}")
    
    def _validate_article(self, article: dict[str, Any]) -> bool:
        """Validate that an article has all required properties."""
        required_fields = ["referenceHeadline", "articleFeaturedImage"]
        article_id = article.get("id", "N/A")
        
        for field in required_fields:
            if not article.get(field):
                self.logger.error(f"Article {article_id}: Missing required property: {field}")
                return False
        
        # Log warnings for optional fields
        optional_fields = ["articleKicker"]
        for field in optional_fields:
            if not article.get(field):
                self.logger.warning(f"Article {article_id}: Missing optional property: {field}")
        
        return True
    
    def _delete_existing_copertine(self, edition_id: str) -> bool:
        """Delete all existing copertine with the given editionId.
        
        Returns:
            bool: True if deletion was successful or no objects existed, False if deletion failed
        """
        try:
            # Check if any objects exist
            existing_objects = self.collection.query.fetch_objects(
                filters=wvc.query.Filter.by_property("editionId").equal(edition_id),
                limit=100
            )
            
            if not existing_objects.objects:
                return True
            
            self.logger.info(f"Found {len(existing_objects.objects)} existing objects with editionId {edition_id}")
            
            # Delete by individual IDs
            uuids_to_delete = [obj.uuid for obj in existing_objects.objects]
            failed_deletions = []
            
            for uuid in uuids_to_delete:
                try:
                    self.collection.data.delete_by_id(uuid)
                except Exception as e:
                    self.logger.error(f"Failed to delete object with UUID {uuid}: {e}")
                    failed_deletions.append(uuid)
            
            if failed_deletions:
                self.logger.error(f"Failed to delete {len(failed_deletions)} objects")
                return False
            
            # Log successful deletion
            self.logger.info(f"Successfully deleted {len(uuids_to_delete)} objects with editionId {edition_id}")
            
            # Verification
            verify_objects = self.collection.query.fetch_objects(
                filters=wvc.query.Filter.by_property("editionId").equal(edition_id),
                limit=10
            )
            
            if verify_objects.objects:
                self.logger.error(f"Deletion verification failed: Still found {len(verify_objects.objects)} objects with editionId {edition_id}")
                return False
            
            return True
                
        except Exception as e:
            self.logger.error(f"Error in deletion operation: {e}")
            return False
    
    def _download_and_save_image(self, article: dict[str, Any], date: datetime) -> str | None:
        """Download and save the article's featured image."""
        image_id = article.get('articleFeaturedImage')
        if not image_id:
            self.logger.error(f"No featured image ID for article {article.get('id')}")
            return None
        
        # Get the actual image URL from Directus
        image_url = self._get_asset_url(image_id)
        if not image_url:
            return None
        
        # Generate filename
        filename = self._generate_image_filename(article, date)
        if not filename:
            return None
        
        # Download the image
        return self._download_image(image_url, filename)
    
    def _get_asset_url(self, image_id: str) -> str | None:
        """Get the asset URL for an image ID."""
        try:
            image_record_url = f"https://directus.ilmanifesto.it/items/images/{image_id}"
            
            response = requests.get(image_record_url, headers=self.directus_headers, timeout=30.0)
            response.raise_for_status()
            
            image_record = response.json().get('data')
            if image_record and "image" in image_record:
                return f"{self.assets_url}/{image_record['image']}"
            else:
                self.logger.error(f"Malformed image record for image ID {image_id}")
                return None
                    
        except requests.RequestException:
            self.logger.exception(f"Error getting asset URL for image {image_id}")
            return None
    
    def _generate_image_filename(self, article: dict[str, Any], date: datetime) -> str | None:
        """Generate a descriptive filename for the image."""
        try:
            headline = article.get("referenceHeadline", "")
            if not headline:
                self.logger.warning(f"No headline for article {article.get('id')}")
                return f"il-manifesto_{date.strftime('%Y-%m-%d')}_no-headline"
            else:
                slug = self._slugify(headline)
                date_str = date.strftime('%Y-%m-%d')
                return f"il-manifesto_{date_str}_{slug}"
            
        except Exception:
            self.logger.exception("Error generating filename")
            return None
    
    def _slugify(self, text: str) -> str:
        """Convert string to a URL-friendly slug."""
        text = text.lower()
        text = re.sub(r'[\s\W]+', '-', text)
        return text.strip('-')
    
    def _download_image(self, image_url: str, base_filename: str) -> str | None:
        """Download image from URL and save to file."""
        try:
            self.logger.info(f"Downloading image from: {image_url}")
            response = requests.get(image_url, headers=self.directus_headers, timeout=30.0)
            response.raise_for_status()
            
            if response.status_code != HTTP_OK:
                self.logger.warning(f"Failed to download image. Status code: {response.status_code}")
                return None
            
            # Determine file extension from content type
            content_type = response.headers.get('content-type')
            if not content_type:
                self.logger.warning(f"No content-type header for image {image_url}")
                extension = '.jpg'  # Fallback
            else:
                extension = mimetypes.guess_extension(content_type) or '.jpg'
            
            # Create full filename with extension
            filename_with_ext = f"{base_filename}{extension}"
            file_path = self.images_dir / filename_with_ext
            
            # Save the image
            file_path.write_bytes(response.content)
            self.logger.info(f"Image saved to {file_path}. Size: {len(response.content)} bytes")
            
            return filename_with_ext
                
        except Exception:
            self.logger.exception(f"Error downloading image {image_url}")
            return None
    
    def _store_in_weaviate(self, article: dict[str, Any], date: datetime, image_filename: str):
        """Store the copertina data in Weaviate."""
        try:
            edition_id = date.strftime("%d-%m-%Y")
            # Format date as RFC3339 string (required by Weaviate)
            # Ensure timezone info is included
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            rfc3339_date = date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            
            data = {
                "testataName": "Il Manifesto",
                "editionId": edition_id,
                "editionDateIsoStr": rfc3339_date,
                "editionImageFnStr": image_filename,
                "captionStr": article.get("referenceHeadline"),
                "kickerStr": article.get("articleKicker"),
            }
            
            insert_result = self.collection.data.insert(properties=data)
            self.logger.info(f"Successfully stored copertina for {edition_id} with UUID {insert_result}")
            
        except Exception:
            self.logger.exception(f"Failed to store data in Weaviate for article {article.get('id')}")
    
    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'weaviate_client') and self.weaviate_client:
            try:
                self.weaviate_client.close()
            except Exception:
                self.logger.exception("Error closing Weaviate client")
            finally:
                self.weaviate_client = None
                self.collection = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def main():
    """Main entry point."""
    try:
        with DirectusManifestoScraper() as scraper:
            # a) Parse command line args to generate list of dates
            dates = scraper.parse_dates_from_args()
            
            # b) Process copertine for all dates
            scraper.process_copertine(dates)
            
        logging.getLogger(__name__).info("Successfully completed copertina processing.")
        
    except ScraperError:
        logging.getLogger(__name__).exception("Scraper error")
        sys.exit(1)
    except Exception:
        logging.getLogger(__name__).exception("Unexpected error")
        sys.exit(1)


if __name__ == "__main__":
    main()
