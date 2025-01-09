from datetime import datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import re
import time
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup
from dotenv import load_dotenv
import httpx
import weaviate
from weaviate.classes.query import Filter

from src.includes.weschema import COPERTINE_COLL_CONFIG

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
IMAGES_DIR = Path("images")

class ManifestoScraper:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        # Initialize Weaviate client
        self.client = self._init_weaviate_client()
        self.collection = self._ensure_collection()
        # Create images directory
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    def _init_weaviate_client(self) -> weaviate.WeaviateClient:
        """Initialize Weaviate client with error handling"""
        try:
            if os.getenv("COP_WEAVIATE_URL") == "localhost":
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
        try:
            COP_COPERTINE_COLLNAME = os.getenv("COP_COPERTINE_COLLNAME")

            # Check if collection exists
            if COP_COPERTINE_COLLNAME not in self.client.collections.list_all():
                collection = self.client.collections.create(
                    name=COPERTINE_COLL_CONFIG["class"],
                    description=COPERTINE_COLL_CONFIG["description"],
                    properties=COPERTINE_COLL_CONFIG["properties"],
                )
                logger.info("Created %s collection in Weaviate", COP_COPERTINE_COLLNAME)
            else:
                collection = self.client.collections.get(COP_COPERTINE_COLLNAME)

            return collection
        except Exception:
            logger.exception("Failed to create collection: %s", COP_COPERTINE_COLLNAME)
            raise

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

    def extract_page_info(self, html_content: str) -> Dict[str, Any]:
        """Extract information from the page HTML"""
        soup = BeautifulSoup(html_content, "html.parser")
        opening_section = soup.find("div", class_="Opening3")

        if not opening_section:
            return {}

        article = opening_section.find("article")
        if not article:
            return {}

        img_tag = article.find("img")
        image_url = img_tag.get("src") if img_tag else None

        title_tag = article.find("h3")
        title = title_tag.get_text().strip() if title_tag else None

        body_tag = article.find("p")
        body = body_tag.get_text().strip() if body_tag else None

        return {
            "image_url": image_url,
            "title": title,
            "body": body,
        }

    def store_in_weaviate(self, date_str: str, page_info: Dict[str, Any], image_filename: str):
        """Store scraped data in Weaviate"""
        try:
            # Convert DD-MM-YYYY to ISO datetime
            date_parts = date_str.split("-")
            iso_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}T00:00:00Z"

            # Get title and body
            title = page_info.get("title", "")
            body = page_info.get("body", "")

            # If body starts with title, remove title and any following whitespace
            if title and body.startswith(title):
                body = body[len(title):].lstrip()

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

    def check_and_get_edition(self, client: httpx.Client, url: str, date_str: str) -> tuple[bool, Optional[httpx.Response]]:
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

    def fetch_manifesto_edition_data(self, start_date: datetime, end_date: datetime) -> Optional[Dict[str, Any]]:
        """Check historical il manifesto URLs and extract content"""
        base_url = "https://ilmanifesto.it/edizioni/il-manifesto/il-manifesto-del-{}"
        results = {}

        client = httpx.Client(timeout=10.0, follow_redirects=True)

        current_date = start_date
        while current_date >= end_date:
            date_str = current_date.strftime("%d-%m-%Y")
            url = base_url.format(date_str)

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
                        image_path = IMAGES_DIR / image_filename
                        if self.download_image(client, page_info["image_url"], image_path):
                            page_info["saved_image"] = str(image_path)
                            logger.info("Downloaded image to %s", image_path)
                            # Store in Weaviate
                            self.store_in_weaviate(date_str, page_info, image_filename)

                    results[date_str] = page_info
                    logger.info(
                        "Date: %s\nTitle: %s\nImage: %s\nBody: %s\n%s",
                        date_str,
                        page_info.get("title"),
                        page_info.get("image_url"),
                        page_info.get("body"),
                        SEPARATOR_LINE,
                    )
                else:
                    logger.warning("No Opening3 section found for %s", date_str)

            time.sleep(1)
            current_date -= timedelta(days=1)

        client.close()

        with OUTPUT_FILE.open("w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        return results

    def __del__(self):
        """Ensure client is properly closed"""
        if hasattr(self, "client"):
            self.client.close()

if __name__ == "__main__":
    try:
        scraper = ManifestoScraper()
        # Start from today with explicit timezone
        start_date = datetime.now(tz=timezone.utc)
        # End date (January 1st, 2025)
        end_date = datetime(2024, 12, 30, tzinfo=timezone.utc)

        scraper.fetch_manifesto_edition_data(start_date, end_date)

    except Exception:
        logger.exception("Application failed")
    finally:
        if "scraper" in locals():
            del scraper
