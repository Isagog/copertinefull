# main.py
from datetime import datetime
import logging
import os
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests
import weaviate

from src.includes.mytypes import Copertina
from src.includes.weschema import COPERTINE_COLL_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

class ManifestoScraper:
    def __init__(self):
        # Load environment variables
        load_dotenv()

        # Create images directory if it doesn't exist
        self.images_dir = "images"
        Path(self.images_dir).mkdir(parents=True, exist_ok=True)

        # Initialize Weaviate client
        self.client = self._init_weaviate_client()
        self._ensure_collection()

    def _init_weaviate_client(self) -> weaviate.WeaviateClient:
        """Initialize Weaviate client with error handling"""
        try:
            if os.getenv("COP_WEAVIATE_URL") == "localhost":
                return weaviate.connect_to_local()
            return weaviate.connect(
                connection_params=weaviate.auth.AuthApiKey(
                    api_key=os.getenv("WEAVIATE_API_KEY"),
                ),
                host=os.getenv("COP_WEAVIATE_URL"),
            )
        except Exception:
            logger.exception("Failed to initialize Weaviate client")
            raise

    def __del__(self):
        """Ensure client is properly closed"""
        if hasattr(self, "client"):
            self.client.close()

    def _ensure_collection(self):
        """Ensure the Copertine collection exists in Weaviate"""
        try:
            COP_COPERTINE_COLLNAME = os.getenv("COP_COPERTINE_COLLNAME")
            if COP_COPERTINE_COLLNAME not in self.client.collections.list_all():
                self.client.collections.create(
                    name=COPERTINE_COLL_CONFIG["class"],
                    description=COPERTINE_COLL_CONFIG["description"],
                    properties=COPERTINE_COLL_CONFIG["properties"],
                )
                logger.info("Created %s collection in Weaviate", COP_COPERTINE_COLLNAME)
        except Exception:
            logger.exception("Failed to create collection: %s", COP_COPERTINE_COLLNAME)
            raise

    def _extract_date_from_filename(self, filename: str) -> Optional[datetime]:
        """Extract date from filename pattern il_manifesto_del_D_MONTH_YYYY_cover.jpg"""
        try:
            # Dictionary to map Italian month names to numbers
            month_map = {
                "gennaio": "01", "febbraio": "02", "marzo": "03",
                "aprile": "04", "maggio": "05", "giugno": "06",
                "luglio": "07", "agosto": "08", "settembre": "09",
                "ottobre": "10", "novembre": "11", "dicembre": "12",
            }

            # Extract the date part from the filename
            date_part = filename.split("_del_")[1].split("_cover")[0]
            day, month_name, year = date_part.split("_")

            # Convert to YYYYMMDD format
            month = month_map[month_name.lower()]
            day = day.zfill(2)  # Pad single digit days with leading zero

            # Construct the date string in YYYY-MM-DD format with timezone
            date_str = f"{year}-{month}-{day}"
            parsed_date = datetime.strptime(date_str + "+0000", "%Y-%m-%d%z")
            return parsed_date.replace(tzinfo=datetime.timezone.utc).date()

        except Exception:
            logger.exception("Failed to extract date from filename %s", filename)
            return None

    def _check_edition_exists(self, edition_date: datetime) -> bool:
        """Check if edition already exists in Weaviate"""
        try:
            # Convert date to RFC3339 format with time
            rfc3339_date = f"{edition_date.isoformat()}T00:00:00Z"
            collection = self.client.collections.get("Copertine")
            result = collection.query.fetch_objects(
                filters=weaviate.classes.query.Filter.by_property("editionDateIsoStr").equal(rfc3339_date),
            )
            return len(result.objects) > 0
        except Exception:
            logger.exception("Failed to check edition existence")
            return False

    def _download_and_save_image(self, img_url: str, filename: str) -> Optional[str]:
        """Download image and save to local directory"""
        try:
            response = requests.get(img_url, timeout=30)
            response.raise_for_status()

            # Save image to local directory using pathlib
            filepath = Path(self.images_dir) / filename
            filepath.write_bytes(response.content)
        except Exception:
            logger.exception("Failed to download/save image %s", img_url)
            return None
        else:
            return filename


    def _process_image_tag(self, img_tag, next_url: str, collection) -> bool:
        """Process a single image tag and store the edition if valid"""
        try:
            img_url = img_tag.get("src")
            if not img_url:
                return False

            full_img_url = urljoin(next_url, img_url)
            filename = Path(full_img_url.split("?")[0]).name

            if not filename.startswith("il_manifesto_del_"):
                return False

            edition_date = self._extract_date_from_filename(filename)
            if not edition_date or self._check_edition_exists(edition_date):
                logger.info("Edition %s already exists or invalid date, skipping", edition_date)
                return False

            saved_filename = self._download_and_save_image(full_img_url, filename)
            if not saved_filename:
                return False

            copertina = Copertina(
                testataName="Il Manifesto",
                editionId=filename,
                editionDateIsoStr=edition_date,
                editionImageStr=saved_filename,
            )
            collection.data.insert(copertina.model_dump())
        except Exception:
            logger.exception("Error processing image tag")
            return False
        else:
            logger.info("Successfully stored edition %s", edition_date)
            return True



    def _get_next_page_url(self, soup, current_url: str, base_url: str) -> str | None:
        """Get the URL of the next page"""
        next_link = soup.find("a", {"aria-label": "Go to next page"})
        if not next_link or not next_link.get("href"):
            logger.info("No next page link found, ending scrape")
            return None

        next_url = urljoin(current_url, next_link["href"])
        if next_url == base_url:
            logger.warning("Pagination led back to the start URL, ending scrape")
            return None

        return next_url

    def scrape_images(self, base_url: str, max_retries: int = 3):
        """Main scraping function"""
        session = requests.Session()
        try:
            next_url = base_url
            collection = self.client.collections.get("Copertine")
            page_count = 0
            retry_count = 0

            while next_url and retry_count < max_retries:
                try:
                    logger.info("Scraping page %d: %s", page_count + 1, next_url)
                    response = session.get(next_url, timeout=30)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, "html.parser")

                    image_tags = soup.select("img.h-auto.w-full.cursor-zoom-in.object-contain")
                    logger.info("Found %d matching image tags", len(image_tags))

                    if not image_tags:
                        logger.warning("No images found on page, might be at the end")
                        if retry_count < max_retries - 1:
                            retry_count += 1
                            logger.info("Retrying %d/%d", retry_count, max_retries)
                            continue
                        logger.info("Max retries reached with no images, ending scrape")
                        break

                    for img_tag in image_tags:
                        self._process_image_tag(img_tag, next_url, collection)

                    # Reset retry count after successful page processing
                    retry_count = 0
                    page_count += 1

                    next_url = self._get_next_page_url(soup, next_url, base_url)

                except requests.Timeout:
                    logger.exception("Timeout while processing page %s", next_url)
                    retry_count += 1
                    if retry_count >= max_retries:
                        logger.exception("Max retries reached due to timeouts")
                        break

                except Exception:
                    logger.exception("Error processing page %s", next_url)
                    retry_count += 1
                    if retry_count >= max_retries:
                        logger.exception("Max retries reached due to errors")
                        break

            logger.info("Scraping completed. Processed %d pages", page_count)
        finally:
            session.close()

if __name__ == "__main__":
    try:
        scraper = ManifestoScraper()
        scraper.scrape_images("https://ilmanifesto.it/ritagli/copertine")
    except Exception:
        logger.exception("Application failed")
    finally:
        # Ensure proper cleanup
        if "scraper" in locals():
            del scraper
