from datetime import datetime, timezone
import json
import logging

from bs4 import BeautifulSoup
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

def extract_page_info(html_content: str):
    """Extract information from the page HTML"""
    soup = BeautifulSoup(html_content, "html.parser")
    logger.info("Page title: %s", soup.title.string if soup.title else "No title found")

    # Find all articles
    articles = soup.find_all("article", class_="PostCard")
    if not articles:
        logger.warning("No articles found")
        return {}

    # Look for the main article - it should be the first one with an image and category
    main_article = None
    for article in articles:
        # Check if it has an image
        img_tag = article.select_one("img[src*='static.ilmanifesto.it'], img[src*='/cdn-cgi/image']")
        if not img_tag:
            continue

        # Check if it has a category
        category_link = article.select_one("a.text-red-500")
        if category_link and "ECONOMIA" in category_link.get_text().strip().upper():
            main_article = article
            logger.info("Found main article with category: %s", category_link.get_text().strip())
            break

    if not main_article:
        logger.warning("No main article found")
        # Log all articles for debugging
        for i, article in enumerate(articles, 1):
            logger.info("Article %d HTML:\n%s", i, article.prettify())
        return {}

    # Get the image URL
    img_tag = main_article.select_one("img[src*='static.ilmanifesto.it'], img[src*='/cdn-cgi/image']")
    image_url = img_tag.get("src") if img_tag else None
    logger.info("Found image URL: %s", image_url)

    # Get the title - try different heading levels
    title = None
    for title_selector in ["h1", "h2", "h3"]:
        title_tag = main_article.find(title_selector)
        if title_tag:
            title = title_tag.get_text().strip()
            logger.info("Found title with selector %s: %s", title_selector, title)
            break

    # Get the author and body text
    author = None
    author_tag = main_article.select_one("span.font-serif.text-sm.italic")
    if author_tag:
        author = author_tag.get_text().strip()
        logger.info("Found author: %s", author)

    # Look for body text
    body = None
    body_tag = main_article.select_one("p.body-ns-1")
    if body_tag:
        # Get the text but exclude any overline text
        overline = body_tag.select_one("span.overline-3")
        if overline:
            overline.decompose()
        body = body_tag.get_text().strip()
        logger.info("Found body text")

    return {
        "image_url": image_url,
        "title": title,
        "author": author,
        "body": body,
    }

if __name__ == "__main__":
    # Test with today's edition
    date_str = datetime.now(tz=timezone.utc).strftime("%d-%m-%Y")
    url = f"https://ilmanifesto.it/edizioni/il-manifesto/il-manifesto-del-{date_str}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True, headers=headers) as client:
            logger.info("Fetching URL: %s", url)
            response = client.get(url)
            if response.status_code == 200:
                page_info = extract_page_info(response.text)
                if page_info:
                    logger.info("\nExtracted information:")
                    logger.info("Title: %s", page_info.get("title"))
                    logger.info("Author: %s", page_info.get("author"))
                    logger.info("Image URL: %s", page_info.get("image_url"))
                    logger.info("Body: %s", page_info.get("body"))

                    # Save to JSON for inspection
                    with open("test_output.json", "w", encoding="utf-8") as f:
                        json.dump(page_info, f, ensure_ascii=False, indent=2)
            else:
                logger.error("Failed to fetch page. Status code: %d", response.status_code)
    except Exception:
        logger.exception("Error occurred")
