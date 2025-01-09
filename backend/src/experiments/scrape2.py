from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Constants
HTTP_STATUS_OK = 200
SEPARATOR_LINE = "-" * 50
OUTPUT_FILE = Path("manifesto_archive.json")
IMAGES_DIR = Path("images")

def transform_image_url_to_full_url(image_url: str) -> str:
    """
    Transform relative image URL to full URL
    Args:
        image_url: Relative or absolute image URL
    Returns:
        str: Full URL
    """
    if image_url.startswith("/"):
        return f"https://ilmanifesto.it{image_url}"
    return image_url

def download_image(client: httpx.Client, image_url: str, filename: Path) -> bool:
    """
    Download image from URL and save to file
    Args:
        client: httpx Client instance
        image_url: URL of the image
        filename: Path where to save the image
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        full_url = transform_image_url_to_full_url(image_url)
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

def transform_image_url_to_filename(image_url: str, date_str: str) -> str:
    """
    Transform CDN URL to a filename following pattern:
    il-manifesto_YYYY-MM-DD_original-filename.jpg
    Args:
        image_url: Original CDN URL
        date_str: Date string in DD-MM-YYYY format
    Returns:
        str: Transformed filename
    """
    # Extract the real image path after /https://
    match = re.search(r"https://static\.ilmanifesto\.it/(?:\d{4}/\d{2}/\d{2})?(.+?)$", image_url)
    if not match:
        # Try alternative pattern for relative URLs
        match = re.search(r"/cdn-cgi/image/[^/]+/https://static\.ilmanifesto\.it/(?:\d{4}/\d{2}/\d{2})?(.+?)$", image_url)
        if not match:
            return ""

    # Get the original filename without date prefix path
    image_path = match.group(1)
    # Replace any remaining slashes with hyphens
    image_path = image_path.replace("/", "-")

    # Convert date from DD-MM-YYYY to YYYY-MM-DD for filename
    date_parts = date_str.split("-")
    formatted_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"

    # Create filename with requested format
    return f"il-manifesto_{formatted_date}_{image_path}"

def extract_page_info(html_content: str) -> Dict[str, Any]:
    """
    Extract information from the page HTML
    Args:
        html_content: HTML content of the page
    Returns:
        dict with extracted information
    """
    soup = BeautifulSoup(html_content, "html.parser")
    opening_section = soup.find("div", class_="Opening3")

    if not opening_section:
        return {}

    # Find the first article in Opening3
    article = opening_section.find("article")
    if not article:
        return {}

    # Extract image URL
    img_tag = article.find("img")
    image_url = img_tag.get("src") if img_tag else None

    # Extract title from h3
    title_tag = article.find("h3")
    title = title_tag.get_text().strip() if title_tag else None

    # Extract body text
    body_tag = article.find("p")
    body = body_tag.get_text().strip() if body_tag else None

    return {
        "image_url": image_url,
        "title": title,
        "body": body,
    }

def check_manifesto_urls(
    start_date: datetime,
    end_date: datetime,
) -> Optional[dict[str, Any]]:
    """
    Check historical il manifesto URLs for existence and extract content
    Args:
        start_date (datetime): Starting date to check from
        end_date (datetime): Date to stop checking at (inclusive)
    Returns:
        dict[str, Any] | None: Dictionary of URLs and their extracted content,
                              or None if there was an error
    """
    base_url = "https://ilmanifesto.it/edizioni/il-manifesto/il-manifesto-del-{}"
    results = {}

    # Create httpx client with timeout and following redirects
    client = httpx.Client(timeout=10.0, follow_redirects=True)

    current_date = start_date
    while current_date >= end_date:
        # Format date as DD-MM-YYYY
        date_str = current_date.strftime("%d-%m-%Y")
        url = base_url.format(date_str)

        try:
            # Use GET instead of HEAD to get the content
            response = client.get(url)
            exists = response.status_code == HTTP_STATUS_OK

            if exists:
                page_info = extract_page_info(response.text)
                if page_info and page_info["image_url"]:
                    # Transform image URL to filename
                    image_filename = transform_image_url_to_filename(
                        page_info["image_url"],
                        date_str,
                    )
                    if image_filename:
                        # Download image
                        image_path = IMAGES_DIR / image_filename
                        if download_image(client, page_info["image_url"], image_path):
                            page_info["saved_image"] = str(image_path)
                            logger.info("Downloaded image to %s", image_path)

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

        except httpx.RequestError:
            logger.exception("Error checking %s", url)
            continue

        # Add small delay to be nice to the server
        time.sleep(1)

        # Go back one day
        current_date -= timedelta(days=1)

    client.close()

    # Save results to JSON file using Path
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results

if __name__ == "__main__":
    # Start from today with explicit timezone
    start_date = datetime.now(tz=timezone.utc)
    # End date (January 1st, 2012)
    end_date = datetime(2025, 1, 1, tzinfo=timezone.utc)

    check_manifesto_urls(start_date, end_date)
