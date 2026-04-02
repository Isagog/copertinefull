""" Scrape Directus 2 — PostgreSQL backend """
import argparse
import logging
import mimetypes
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import psycopg2
import requests
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

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


class DirectusManifestoScraper:
    """Scraper for Il Manifesto copertina articles from Directus CMS."""

    def __init__(self):
        self._setup_logging()
        self._load_environment()
        self._init_db()
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
        for lib in ["httpx", "httpcore"]:
            logging.getLogger(lib).setLevel(logging.WARNING)

        self.logger = logging.getLogger(__name__)

    def _load_environment(self):
        """Load environment variables from project root .secrets."""
        secrets_path = Path(__file__).parents[2] / '.secrets'
        load_dotenv(dotenv_path=secrets_path, override=True)

    def _get_required_env(self, var_name: str) -> str:
        """Get a required environment variable or raise an error."""
        value = os.getenv(var_name)
        if value is None:
            raise MissingEnvironmentVariableError(var_name)
        return value

    def _init_db(self):
        """Initialize PostgreSQL connection."""
        database_url = self._get_required_env("DATABASE_URL")
        try:
            self.db_conn = psycopg2.connect(database_url)
            self.db_conn.autocommit = False
            self.logger.info("Connected to PostgreSQL")
        except Exception:
            self.logger.exception("Failed to connect to PostgreSQL")
            raise

    def _upsert_edition(self, edition_id: str, edition_date: datetime,
                        caption: str, kicker: str | None, image_filename: str):
        """Upsert a copertina edition into PostgreSQL."""
        sql = """
            INSERT INTO editions (edition_id, edition_date, caption, kicker, image_filename)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (edition_id) DO UPDATE SET
                caption = EXCLUDED.caption,
                kicker = EXCLUDED.kicker,
                image_filename = EXCLUDED.image_filename,
                updated_at = now();
        """
        date_only = edition_date.date() if hasattr(edition_date, 'date') else edition_date
        try:
            with self.db_conn.cursor() as cur:
                cur.execute(sql, (edition_id, date_only, caption, kicker, image_filename))
            self.db_conn.commit()
            self.logger.info(f"Upserted edition {edition_id} into PostgreSQL")
        except Exception:
            self.db_conn.rollback()
            self.logger.exception(f"Failed to upsert edition {edition_id}")
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
            description="Fetch Il Manifesto copertina articles from Directus CMS and store in PostgreSQL"
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
        return []

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
                return articles[0]

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

        # Download image
        image_filename = self._download_and_save_image(article, date)
        if image_filename:
            self._upsert_edition(
                edition_id=edition_id,
                edition_date=date,
                caption=article.get("referenceHeadline", ""),
                kicker=article.get("articleKicker"),
                image_filename=image_filename,
            )
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

        except Exception:
            self.logger.exception(f"Error downloading image {image_url}")
            return None
        else:
            return filename_with_ext

    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'db_conn') and self.db_conn:
            try:
                self.db_conn.close()
                self.logger.info("PostgreSQL connection closed")
            except Exception:
                self.logger.exception("Error closing PostgreSQL connection")

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
