from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import time
from http import HTTPStatus

from bs4 import BeautifulSoup
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

def extract_page_info(html_content: str) -> dict:
    """Extract information from the page HTML"""
    soup = BeautifulSoup(html_content, "html.parser")

    # Find all articles
    articles = soup.find_all("article", class_="PostCard")
    if not articles:
        logger.warning("No articles found")
        return {}

    # Look for the main article - it should be the first one with:
    # 1. A large image (in a div.w-full)
    # 2. A category link
    # 3. A title in h3
    main_article = None
    for article in articles:
        # Check if it has a large image container
        img_container = article.select_one("div.w-full.overflow-hidden.order-1")
        if not img_container:
            continue

        # Check if it has an image
        img_tag = img_container.select_one("img[src*='static.ilmanifesto.it'], img[src*='/cdn-cgi/image']")
        if not img_tag:
            continue

        # Check if it has a category
        category_link = article.select_one("a.text-red-500")
        if not category_link:
            continue

        # Check if it has a title
        title_tag = article.find("h3")
        if not title_tag:
            continue

        main_article = article
        break

    if not main_article:
        logger.warning("No main article found")
        return {}

    # Get the category
    category_link = main_article.select_one("a.text-red-500")
    category = category_link.get_text().strip() if category_link else None

    # Get the image URL
    img_tag = main_article.select_one("img[src*='static.ilmanifesto.it'], img[src*='/cdn-cgi/image']")
    image_url = img_tag.get("src") if img_tag else None

    # Get the title
    title = None
    title_tag = main_article.find("h3")
    if title_tag:
        title = title_tag.get_text().strip()

    # Get the author
    author = None
    author_tag = main_article.select_one("span.font-serif.text-sm.italic")
    if author_tag:
        author = author_tag.get_text().strip()

    # Get the body text
    body = None
    body_tag = main_article.select_one("p.body-ns-1")
    if body_tag:
        # Get the text but exclude any overline text
        overline = body_tag.select_one("span.overline-3")
        if overline:
            overline.decompose()
        body = body_tag.get_text().strip()

    return {
        "category": category,
        "title": title,
        "author": author,
        "image_url": image_url,
        "body": body,
    }

def check_past_dates(num_days: int = 10):
    """Check articles from the past num_days"""
    base_url = "https://ilmanifesto.it/edizioni/il-manifesto/il-manifesto-del-{}"
    results = {}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    with httpx.Client(timeout=30.0, follow_redirects=True, headers=headers) as client:
        # Start from today and go back num_days
        current_date = datetime.now(tz=timezone.utc)
        for i in range(num_days):
            date_str = current_date.strftime("%d-%m-%Y")
            url = base_url.format(date_str)

            logger.info("\nChecking date: %s", date_str)
            logger.info("URL: %s", url)

            try:
                response = client.get(url)
                if response.status_code == HTTPStatus.OK:
                    page_info = extract_page_info(response.text)
                    if page_info:
                        results[date_str] = page_info
                        logger.info("Found article:")
                        logger.info("Category: %s", page_info.get("category"))
                        logger.info("Title: %s", page_info.get("title"))
                        logger.info("Author: %s", page_info.get("author"))
                        logger.info("Image: %s", page_info.get("image_url"))
                        logger.info("Body: %s", page_info.get("body")[:100] + "..." if page_info.get("body") else None)
                    else:
                        logger.warning("No article found for date %s", date_str)
                else:
                    logger.warning("Failed to fetch page for date %s. Status code: %d", date_str, response.status_code)
            except Exception as e:
                logger.exception("Error processing date %s", date_str)

            # Move to previous day
            current_date -= timedelta(days=1)
            # Small delay between requests
            if i < num_days - 1:  # Don't sleep after the last request
                time.sleep(1)

    # Save results to JSON for inspection
    output_file = Path("test_results.json")
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info("\nResults saved to %s", output_file)

if __name__ == "__main__":
    check_past_dates(10)
