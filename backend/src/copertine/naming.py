"""The archive's file-naming convention.

Product, not CMS: the 4500 covers already on disk are named this way and the
frontend serves them by that name, so this is the one part of the old scraper
that must not change.
"""

import mimetypes
import re
from datetime import date

from corpus import AssetRef

#: What the archive has always used when the CMS declares nothing usable.
FALLBACK_EXTENSION = ".jpg"

_NON_WORD = re.compile(r"[\s\W]+")


def slugify(text: str) -> str:
    """Lowercase, non-word runs collapsed to single hyphens."""
    return _NON_WORD.sub("-", text.lower()).strip("-")


def image_filename(edition_date: date, headline: str, image: AssetRef) -> str:
    """`il-manifesto_YYYY-MM-DD_slug.jpg`, unchanged from the old scraper.

    The extension comes from the CMS's own file record rather than from the
    downloaded bytes, so it is known before anything is fetched.
    """
    slug = slugify(headline) or "no-headline"
    return f"il-manifesto_{edition_date.isoformat()}_{slug}{_extension(image)}"


def edition_id(edition_date: date) -> str:
    """The `editions.edition_id` primary key: DD-MM-YYYY."""
    return edition_date.strftime("%d-%m-%Y")


def _extension(image: AssetRef) -> str:
    if not image.mime:
        return FALLBACK_EXTENSION
    return mimetypes.guess_extension(image.mime) or FALLBACK_EXTENSION
