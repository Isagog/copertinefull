# main.py
import logging
import os
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import requests
import weaviate
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from src.includes.mytypes import Copertina
from src.includes.weschema import COPERTINE_COLL_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ManifestoScraper:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Create images directory if it doesn't exist
        self.images_dir = "images"
        os.makedirs(self.images_dir, exist_ok=True)
        
        # Initialize Weaviate client
        self.client = self._init_weaviate_client()
        self._ensure_collection()
        
    def _init_weaviate_client(self) -> weaviate.WeaviateClient:
        """Initialize Weaviate client with error handling"""
        try:
            if os.getenv("COP_WEAVIATE_URL") == "localhost":
                client = weaviate.connect_to_local()
            else:
                client = weaviate.connect(
                    connection_params=weaviate.auth.AuthApiKey(
                        api_key=os.getenv("WEAVIATE_API_KEY")
                    ),
                    host=os.getenv("COP_WEAVIATE_URL")
                )
            return client
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate client: {str(e)}")
            raise
        
    def __del__(self):
        """Ensure client is properly closed"""
        if hasattr(self, 'client'):
            self.client.close()

    def _ensure_collection(self):
        """Ensure the Copertine collection exists in Weaviate"""
        try:
            COP_COPERTINE_COLLNAME = os.getenv("COP_COPERTINE_COLLNAME")
            if COP_COPERTINE_COLLNAME not in self.client.collections.list_all():
                self.client.collections.create(
                    name=COPERTINE_COLL_CONFIG["class"],
                    description=COPERTINE_COLL_CONFIG["description"],
                    properties=COPERTINE_COLL_CONFIG["properties"]
                )
                logger.info("Created %s collection in Weaviate", COP_COPERTINE_COLLNAME)
        except Exception as e:
            logger.error(f"Failed to create %s collection: {str(e)}", COP_COPERTINE_COLLNAME)
            raise

    def _extract_date_from_filename(self, filename: str) -> Optional[datetime]:
        """Extract date from filename pattern il_manifesto_del_D_MONTH_YYYY_cover.jpg"""
        try:
            # Dictionary to map Italian month names to numbers
            month_map = {
                'gennaio': '01',
                'febbraio': '02',
                'marzo': '03',
                'aprile': '04',
                'maggio': '05',
                'giugno': '06',
                'luglio': '07',
                'agosto': '08',
                'settembre': '09',
                'ottobre': '10',
                'novembre': '11',
                'dicembre': '12'
            }
            
            # Extract the date part from the filename
            date_part = filename.split('_del_')[1].split('_cover')[0]  # Get "D_MONTH_YYYY"
            day, month_name, year = date_part.split('_')
            
            # Convert to YYYYMMDD format
            month = month_map[month_name.lower()]
            day = day.zfill(2)  # Pad single digit days with leading zero
            
            # Construct the date string in YYYY-MM-DD format
            date_str = f"{year}-{month}-{day}"
            return datetime.strptime(date_str, '%Y-%m-%d').date()
            
        except Exception as e:
            logger.error(f"Failed to extract date from filename {filename}: {str(e)}")
            return None

    def _check_edition_exists(self, edition_date: datetime) -> bool:
        """Check if edition already exists in Weaviate"""
        try:
            # Convert date to RFC3339 format with time
            rfc3339_date = f"{edition_date.isoformat()}T00:00:00Z"
            collection = self.client.collections.get("Copertine")
            result = collection.query.fetch_objects(
                filters=weaviate.classes.query.Filter.by_property("editionDateIsoStr").equal(rfc3339_date)
            )
            return len(result.objects) > 0
        except Exception as e:
            logger.error(f"Failed to check edition existence: {str(e)}")
            return False

    def _download_and_save_image(self, img_url: str, filename: str) -> Optional[str]:
        """Download image and save to local directory"""
        try:
            response = requests.get(img_url)
            response.raise_for_status()
            
            # Save image to local directory
            filepath = os.path.join(self.images_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            return filename
        except Exception as e:
            logger.error(f"Failed to download/save image {img_url}: {str(e)}")
            return None

    def scrape_images(self, base_url: str, max_retries: int = 3):
        """Main scraping function"""
        session = requests.Session()
        next_url = base_url
        collection = self.client.collections.get("Copertine")
        page_count = 0
        retry_count = 0

        while next_url and retry_count < max_retries:
            try:
                logger.info(f"Scraping page {page_count + 1}: {next_url}")
                response = session.get(next_url, timeout=30)  # Add timeout
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                image_tags = soup.select('img.h-auto.w-full.cursor-zoom-in.object-contain')
                logger.info(f"Found {len(image_tags)} matching image tags")
                
                if not image_tags:
                    logger.warning("No images found on page, might be at the end")
                    if retry_count < max_retries - 1:
                        retry_count += 1
                        logger.info(f"Retrying {retry_count}/{max_retries}")
                        continue
                    else:
                        logger.info("Max retries reached with no images, ending scrape")
                        break

                for img_tag in image_tags:
                    img_url = img_tag.get('src')
                    if not img_url:
                        continue

                    full_img_url = urljoin(next_url, img_url)
                    filename = os.path.basename(full_img_url.split('?')[0])
                    
                    if not filename.startswith('il_manifesto_del_'):
                        continue

                    edition_date = self._extract_date_from_filename(filename)
                    if not edition_date:
                        continue

                    if self._check_edition_exists(edition_date):
                        logger.info(f"Edition {edition_date} already exists, skipping")
                        continue

                    saved_filename = self._download_and_save_image(full_img_url, filename)
                    if not saved_filename:
                        continue

                    try:
                        copertina = Copertina(
                            testataName="Il Manifesto",
                            editionId=filename,
                            editionDateIsoStr=edition_date,
                            editionImageStr=saved_filename
                        )
                        
                        collection.data.insert(copertina.model_dump())
                        logger.info(f"Successfully stored edition {edition_date}")
                    except Exception as e:
                        logger.error(f"Failed to store edition {edition_date}: {str(e)}")

                # Reset retry count after successful page processing
                retry_count = 0
                page_count += 1

                # More robust pagination handling
                next_link = soup.find('a', {'aria-label': 'Go to next page'})
                if next_link and next_link.get('href'):
                    next_url = urljoin(next_url, next_link['href'])
                    # Verify we're not stuck on the same URL
                    if next_url == base_url:
                        logger.warning("Pagination led back to the start URL, ending scrape")
                        break
                else:
                    logger.info("No next page link found, ending scrape")
                    break
                
            except requests.Timeout:
                logger.error(f"Timeout while processing page {next_url}")
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error("Max retries reached due to timeouts")
                    break
                    
            except Exception as e:
                logger.error(f"Error processing page {next_url}: {str(e)}")
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error("Max retries reached due to errors")
                    break

        logger.info(f"Scraping completed. Processed {page_count} pages")
        session.close()

if __name__ == '__main__':
    try:
        scraper = ManifestoScraper()
        scraper.scrape_images("https://ilmanifesto.it/ritagli/copertine")
    except Exception as e:
        logger.error(f"Application failed: {str(e)}")
    finally:
        # Ensure proper cleanup
        if 'scraper' in locals():
            del scraper
if __name__ == '__main__':
    try:
        scraper = ManifestoScraper()
        scraper.scrape_images("https://ilmanifesto.it/ritagli/copertine")
    except Exception as e:
        logger.error(f"Application failed: {str(e)}")