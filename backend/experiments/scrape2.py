import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import weaviate
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from weaviate.classes.query import Filter, Sort

from includes.weschema import COPERTINE_COLL_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Constants
HTTP_STATUS_OK = 200
SEPARATOR_LINE = "-" * 50
OUTPUT_FILE = Path("manifesto_archive.json")
MISSING_ENV_VAR_MSG = "COPERTINE_OLDEST_DATE environment variable must be set (format: YYYY-MM-DD)"
INVALID_DATE_FORMAT_MSG = "Invalid start date format. Expected YYYY-MM-DD."
MISSING_IMAGES_DIR_MSG = "COP_IMAGES_DIR environment variable must be set"

class ManifestoScraper:
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
        # Check if JSON saving is enabled
        self.save_to_json = os.getenv("COP_SAVE_TO_JSON", "false").lower() == "true"

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
            # Check if collection exists
            collections = self.client.collections.list_all()
            if cop_copertine_collname not in collections:
                collection = self.client.collections.create(
                    name=cop_copertine_collname,
                    description=COPERTINE_COLL_CONFIG["description"],
                    vectorizer_config=None,
                    properties=COPERTINE_COLL_CONFIG["properties"],
                )
                logger.info("Created %s collection in Weaviate", cop_copertine_collname)
            else:
                collection = self.client.collections.get(cop_copertine_collname)
        except Exception:
            logger.exception("Failed to create collection: %s", cop_copertine_collname)
            raise

        return collection

    def transform_image_url_to_full_url(self, image_url: str) -> str:
        """Transform relative image URL to full URL"""
        if image_url.startswith("/"):
            return f"https://ilmanifesto.it{image_url}"
        return image_url

    def download_image(self, client: httpx.Client, image_url: str, filename: Path) -> bool:
        """Download image from URL and save to file"""
        try:
            full_url = self.transform_image_url_to_full_url(image_url)
            logger.info("Attempting to download image from: %s", full_url)
            response = client.get(full_url)
            logger.info("Response status: %d", response.status_code)
            logger.info("Response headers: %s", response.headers)
        except httpx.RequestError:
            logger.exception("Error downloading image %s", image_url)
            return False
        else:
            if response.status_code == HTTP_STATUS_OK:
                try:
                    abs_path = filename.resolve()
                    logger.info("Creating directory: %s", abs_path.parent)
                    abs_path.parent.mkdir(parents=True, exist_ok=True)

                    logger.info("Saving image to: %s", abs_path)
                    abs_path.write_bytes(response.content)
                except Exception:
                    logger.exception("Error saving image to %s", abs_path)
                    return False
                else:
                    logger.info("Image saved successfully. Size: %d bytes", len(response.content))
                    return True

            logger.warning("Failed to download image. Status code: %d", response.status_code)
            return False

    def transform_image_url_to_filename(self, image_url: str, date_str: str) -> str:
        """Transform CDN URL to filename"""
        match = re.search(r"https://static\.ilmanifesto\.it/(?:\d{4}/\d{2}/\d{2})?(.+?)$", image_url)
        if not match:
            match = re.search(r"/cdn-cgi/image/[^/]+/https://static\.ilmanifesto\.it/(?:\d{4}/\d{2}/\d{2})?(.+?)$", image_url)
            if not match:
                return ""

        image_path = match.group(1)
        image_path = image_path.replace("/", "-")

        date_parts = date_str.split("-")
        formatted_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"

        return f"il-manifesto_{formatted_date}_{image_path}"

    def _find_main_article(self, articles: list) -> BeautifulSoup | None:
        """Find the main article from a list of articles."""
        for article in articles:
            if not self._has_required_elements(article):
                continue
            
            logger.info("Found main article with category: %s", 
                       article.select_one("a.text-red-500").get_text().strip())
            return article
        
        logger.warning("No main article found")
        return None

    def _has_required_elements(self, article: BeautifulSoup) -> bool:
        """Check if article has all required elements."""
        # Check image container and image
        img_container = article.select_one("div.w-full.overflow-hidden.order-1")
        if not img_container:
            return False

        img_tag = img_container.select_one("img[src*='static.ilmanifesto.it'], img[src*='/cdn-cgi/image']")
        if not img_tag:
            return False

        # Check category and title
        if not article.select_one("a.text-red-500"):
            return False

        if not article.find("h3"):
            return False

        return True

    def _extract_title(self, article: BeautifulSoup) -> str | None:
        """Extract title from article."""
        for title_selector in ["h1", "h2", "h3"]:
            title_tag = article.find(title_selector)
            if title_tag:
                title = title_tag.get_text().strip()
                logger.info("Found title with selector %s: %s", title_selector, title)
                return title
        return None

    def _extract_body(self, article: BeautifulSoup) -> str | None:
        """Extract body text from article."""
        body_tag = article.select_one("p.body-ns-1")
        if body_tag:
            # Get the text but exclude any overline text
            overline = body_tag.select_one("span.overline-3")
            if overline:
                overline.decompose()
            body = body_tag.get_text().strip()
            logger.info("Found body text")
            return body
        return None

    def extract_page_info(self, html_content: str) -> dict[str, Any]:
        """Extract information from the page HTML"""
        soup = BeautifulSoup(html_content, "html.parser")
        logger.info("Page title: %s", soup.title.string if soup.title else "No title found")

        # Find all articles
        articles = soup.find_all("article", class_="PostCard")
        if not articles:
            logger.warning("No articles found")
            return {}

        main_article = self._find_main_article(articles)
        if not main_article:
            return {}

        # Get the image URL
        img_tag = main_article.select_one("img[src*='static.ilmanifesto.it'], img[src*='/cdn-cgi/image']")
        image_url = img_tag.get("src") if img_tag else None
        logger.info("Found image URL: %s", image_url)

        # Get the author
        author_tag = main_article.select_one("span.font-serif.text-sm.italic")
        author = author_tag.get_text().strip() if author_tag else None
        if author:
            logger.info("Found author: %s", author)

        return {
            "image_url": image_url,
            "title": self._extract_title(main_article),
            "author": author,
            "body": self._extract_body(main_article),
        }

    def store_in_weaviate(self, date_str: str, page_info: dict[str, Any], image_filename: str):
        """Store scraped data in Weaviate"""
        try:
            # Convert DD-MM-YYYY to ISO datetime
            date_parts = date_str.split("-")
            iso_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}T00:00:00Z"

            # Get title and body
            title = page_info.get("title", "")
            body = page_info.get("body", "")
            author = page_info.get("author", "")

            # If body starts with title, remove title and any following whitespace
            if title and body.startswith(title):
                body = body[len(title):].lstrip()

            # If author is in the body, remove it
            if author and body.startswith(author):
                body = body[len(author):].lstrip()

            data = {
                "testataName": "Il Manifesto",
                "editionId": date_str,
                "editionDateIsoStr": iso_date,
                "editionImageFnStr": image_filename,
                "captionStr": title,
                "kickerStr": body,
            }

            # Create object using V4 syntax
            self.collection.data.insert(data)
            logger.info("Successfully stored data in Weaviate for date %s", date_str)
        except Exception:
            logger.exception("Failed to store data in Weaviate for date %s", date_str)

    def _check_edition_exists(self, date_str: str) -> bool:
        """Check if edition already exists in Weaviate"""
        try:
            result = self.collection.query.fetch_objects(
                filters=Filter.by_property("editionId").equal(date_str),
                limit=1,
            )
            return len(result.objects) > 0
        except Exception:
            logger.exception("Failed to check edition existence in Weaviate collection %s for date %s", os.getenv("COP_COPERTINE_COLLNAME"), date_str)
            return False

    @staticmethod
    def check_url_exists(client: httpx.Client, url: str) -> bool:
        """Check if a given URL exists and returns a valid response."""
        try:
            response = client.get(url)
        except httpx.RequestError:
            logger.exception("Error checking %s", url)
            return False
        else:
            return response.status_code == HTTP_STATUS_OK

    def check_and_get_edition(self, client: httpx.Client, url: str, date_str: str) -> tuple[bool, httpx.Response | None]:
        """Check if edition exists at URL and hasn't been processed yet."""
        edition_exists = self.check_url_exists(client, url)

        if not edition_exists:
            return False, None

        logger.info("Found edition URL for date %s", date_str)

        # Check if already in Weaviate
        edition_in_collection = self._check_edition_exists(date_str)
        if edition_in_collection:
            logger.info("Edition for date %s already in Weaviate collection, skipping", date_str)
            return False, None

        # Get the actual response for processing
        try:
            response = client.get(url)
        except httpx.RequestError:
            logger.exception("Error fetching %s", url)
            return False, None
        else:
            return True, response

    def fetch_manifesto_edition_data(self, newest_date: datetime, oldest_date: datetime) -> dict[str, Any] | None:
        """Check historical il manifesto URLs and extract content, starting from newest to oldest"""
        base_url = "https://ilmanifesto.it/edizioni/il-manifesto/il-manifesto-del-{}"
        results = {}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        client = httpx.Client(timeout=30.0, follow_redirects=True, headers=headers)

        try:
            # Start from newest_date and iterate backwards towards oldest_date
            current_date = newest_date
            while current_date >= oldest_date:
                date_str = current_date.strftime("%d-%m-%Y")
                url = base_url.format(date_str)
                logger.info("Trying URL: %s", url)

                should_process, response = self.check_and_get_edition(client, url, date_str)

                if should_process and response:
                    # Process new edition
                    logger.info("Processing new edition for date %s", date_str)
                    page_info = self.extract_page_info(response.text)
                    if page_info and page_info["image_url"]:
                        image_filename = self.transform_image_url_to_filename(
                            page_info["image_url"],
                            date_str,
                        )
                        if image_filename:
                            image_path = self.images_dir / image_filename
                            if self.download_image(client, page_info["image_url"], image_path):
                                page_info["saved_image"] = str(image_path)
                                logger.info("Downloaded image to %s", image_path)
                                # Store in Weaviate
                                self.store_in_weaviate(date_str, page_info, image_filename)

                        if self.save_to_json:
                            results[date_str] = page_info
                            logger.info(
                                "Date: %s\nTitle: %s\nAuthor: %s\nImage: %s\nBody: %s\n%s",
                                date_str,
                                page_info.get("title"),
                                page_info.get("author"),
                                page_info.get("image_url"),
                                page_info.get("body"),
                                SEPARATOR_LINE,
                            )
                    else:
                        logger.warning("No article content found for %s", date_str)

                time.sleep(1)
                current_date -= timedelta(days=1)

        finally:
            client.close()

        # Only save to JSON file if enabled
        if self.save_to_json:
            logger.info("Saving results to JSON file")
            with OUTPUT_FILE.open("w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

        return results if self.save_to_json else None

    def __del__(self):
        """Ensure client is properly closed"""
        if hasattr(self, "client"):
            self.client.close()

    def get_most_recent_edition_date(self) -> datetime | None:
        """Get the most recent edition date from Weaviate collection"""
        try:
            # Query with sort by editionDateIsoStr in descending order
            result = self.collection.query.fetch_objects(
                sort=Sort.by_property(name="editionDateIsoStr", ascending=False),
                limit=1,
            )
        except Exception:
            logger.exception("Failed to get most recent edition date from Weaviate")
            return None
        else:
            if result.objects:
                try:
                    # Get the date from properties
                    latest_date = result.objects[0].properties["editionDateIsoStr"]
                    logger.info("Found latest date: %s (%s)", latest_date, type(latest_date))

                    # If it's already a datetime, just ensure timezone
                    if isinstance(latest_date, datetime):
                        return latest_date.replace(tzinfo=timezone.utc)

                    # If it's a string in our known format
                    return datetime.fromisoformat(str(latest_date))
                except (ValueError, KeyError):
                    logger.exception("Error parsing date from Weaviate")
                    return None
            return None

    def cleanup(self):
        """Explicit cleanup method to ensure resources are properly released"""
        if self.client:
            try:
                self.client.close()
            except Exception:
                logger.exception("Error while closing Weaviate client")
            finally:
                self.client = None
                self.collection = None

    def __enter__(self):
        """Support for context manager protocol"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure cleanup when used as context manager"""
        self.cleanup()

if __name__ == "__main__":
    try:
        scraper = ManifestoScraper()
        newest_date = datetime.now(tz=timezone.utc)

        # Get most recent date from collection
        most_recent_stored_date = scraper.get_most_recent_edition_date()

        if most_recent_stored_date:
            # Check if most recent date is today
            if most_recent_stored_date.date() >= newest_date.date():
                logger.info("Already up to date. No new editions to fetch.")
                sys.exit(0)

            # We'll scrape from today back until the day after the most recent found
            oldest_date = most_recent_stored_date + timedelta(days=1)
        else:
            # No editions found, use configured start date as oldest_date
            oldest_date_str = os.getenv("COPERTINE_OLDEST_DATE")

            def validate_start_date():
                """Validate and parse the start date from environment."""
                if not oldest_date_str:
                    raise ValueError(MISSING_ENV_VAR_MSG)  # noqa: TRY301

                try:
                    # Parse with timezone info to fix DTZ007
                    return datetime.strptime(f"{oldest_date_str} +0000", "%Y-%m-%d %z")
                except ValueError:
                    logger.exception("Invalid date format")
                    raise ValueError(INVALID_DATE_FORMAT_MSG) from None

            oldest_date = validate_start_date()
            logger.info("No editions found in collection, using configured start date %s", oldest_date_str)

        # Log the date range we'll be scraping
        logger.info("\n%s\nScraping editions from newest (%s) to oldest (%s)\n%s",
                   SEPARATOR_LINE,
                   newest_date.strftime("%Y-%m-%d %H:%M %Z"),
                   oldest_date.strftime("%Y-%m-%d %H:%M %Z"),
                   SEPARATOR_LINE)

        scraper.fetch_manifesto_edition_data(newest_date, oldest_date)

    except Exception:
        logger.exception("Application failed")
    finally:
        if "scraper" in locals():
            del scraper
