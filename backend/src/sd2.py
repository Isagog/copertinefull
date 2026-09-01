"""Fetch il manifesto's front pages from the CMS into Postgres.

Reads through the `corpus` port: this file names no Directus field, no filter
grammar and no endpoint. Retargeting a renamed instance is a `DirectusSchema`
constant in `isagog-corpus`; a different CMS is a different adapter.

WHY THIS NO LONGER DOES TIMEZONE ARITHMETIC
-------------------------------------------
The previous version queried *articles* by `datePublished`, which is true UTC,
while il manifesto publishes each cover at Rome-local midnight — 22:00-23:00
UTC the day before. Half this file was Rome-local window maths, a
belt-and-braces re-derivation of the edition date, and a Monday special case.

Editions carry `editionDate`, a plain calendar day, so asking for the edition
of a date is exact. A day the paper does not publish simply has no edition,
which is why Monday needs no special handling any more.
"""

import argparse
import asyncio
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from corpus import (
    Capability,
    Corpus,
    CorpusError,
    CorpusRequirements,
    DocumentNotFound,
    EditionQuery,
    InvalidDocument,
)
from corpus_directus import MANIFESTO_WP_SCHEMA, DirectusCorpus

from copertine.config import (
    MissingEnvironmentVariableError,
    Settings,
    load_settings,
    setup_logging,
)
from copertine.naming import edition_id, image_filename
from copertine.store import EditionStore

#: The archive is keyed on Rome calendar days, so "today" must be Rome's today
#: — the container runs with TZ=UTC, where a late-evening run would otherwise
#: ask for the wrong day.
ROME_TZ = ZoneInfo("Europe/Rome")

#: Checked once at startup, so a backend that cannot serve front pages says so
#: on day one as a printed list rather than as a crash in week three.
REQUIREMENTS = CorpusRequirements(
    required=frozenset({Capability.EDITIONS, Capability.EDITION_COVER, Capability.ASSETS})
)

logger = logging.getLogger("copertine")


class InvalidDateFormatError(ValueError):
    def __init__(self, value: str) -> None:
        super().__init__(f"Invalid date format for '{value}'. Expected YYYY-MM-DD format.")


class DateFileNotFoundError(FileNotFoundError):
    def __init__(self, path: str) -> None:
        super().__init__(f"Date file not found: {path}")


# --- CLI --------------------------------------------------------------------
def parse_dates() -> list[date]:
    parser = argparse.ArgumentParser(
        description="Fetch il manifesto front pages from the CMS and store them in PostgreSQL"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-n", "--number", type=int,
        help="Number of days to fetch ending today (e.g. -n 7 for the last 7 days)",
    )
    group.add_argument("--date", type=str, help="A single date, YYYY-MM-DD")
    group.add_argument(
        "--datefile", type=str, help="File of dates to fetch, one YYYY-MM-DD per line"
    )
    args = parser.parse_args()

    if args.number:
        return _recent_days(args.number)
    if args.date:
        return [_parse_day(args.date)]
    return _read_date_file(args.datefile)


def _recent_days(count: int) -> list[date]:
    """Rome's today, backwards — not the host's, and not UTC's."""
    today = datetime.now(tz=ROME_TZ).date()
    return [today - timedelta(days=offset) for offset in range(count)]


def _parse_day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as err:
        raise InvalidDateFormatError(value) from err


def _read_date_file(path: str) -> list[date]:
    date_file = Path(path)
    if not date_file.is_file():
        raise DateFileNotFoundError(path)

    days: list[date] = []
    for number, line in enumerate(date_file.read_text().splitlines(), 1):
        text = line.strip()
        if not text:
            continue
        try:
            days.append(_parse_day(text))
        except InvalidDateFormatError as err:
            logger.warning("Line %d: %s", number, err)
    return days


# --- the work ---------------------------------------------------------------
async def store_cover(corpus: Corpus, store: EditionStore, day: date, settings: Settings) -> None:
    """Fetch one day's front page and upsert it. Never raises for an ordinary
    absence — only genuine failures reach the caller."""
    editions = await corpus.list_editions(EditionQuery(date_exact=day))
    if not editions:
        # Not an error: the paper does not publish every day (no Monday
        # edition since 2024-06-10), and today's may not be out yet.
        logger.info("No edition published on %s", day)
        return
    if len(editions) > 1:
        # Unreachable while the corpus is scoped to the `wp` series, which has
        # one edition per date across its whole range. Kept as a tripwire: if
        # the scoping is ever lost the archive would start taking whichever
        # edition of an overlapping series came back first, and a wrong
        # headline in a NOT NULL column is not something to discover later.
        logger.error(
            "%d editions dated %s (%s) — ambiguous, skipping",
            len(editions),
            day,
            ", ".join(ref.id for ref in editions),
        )
        return
    edition = editions[0]

    try:
        cover = await corpus.get_edition_cover(edition.id)
    except DocumentNotFound:
        logger.warning("Edition %s (%s) has no front page", edition.id, day)
        return
    except InvalidDocument as err:
        # The display headline is null across the pre-2015 archive. Skipping
        # keeps a blank caption out of a NOT NULL column.
        logger.warning("Edition %s (%s) has an unusable front page: %s", edition.id, day, err)
        return

    if cover.image is None:
        logger.error("Front page of %s carries no image", day)
        return

    filename = image_filename(day, cover.headline, cover.image)
    payload = await corpus.fetch_asset(cover.image.id, max_bytes=settings.max_image_bytes)
    (settings.images_dir / filename).write_bytes(payload)
    logger.info("Saved %s (%d bytes)", filename, len(payload))

    store.upsert(
        edition_id=edition_id(day),
        edition_date=day,
        caption=cover.headline,
        # The column is nullable and the old scraper wrote NULL, not "".
        kicker=cover.kicker or None,
        image_filename=filename,
    )


async def run(days: list[date], settings: Settings) -> None:
    # MANIFESTO_WP_SCHEMA scopes editions to the `wp` import series. The CMS
    # holds four overlapping series (mema, athenaPre2002, athena, wp), so
    # without this a date in 2018-2023 resolves to two different editions and
    # nothing in the row says which is authoritative. `wp` is the live one —
    # 4165 editions on 4165 distinct dates, starting 2013-03-27, which is
    # exactly where this archive begins.
    corpus = DirectusCorpus(
        base_url=settings.directus_url,
        api_key=settings.directus_token,
        schema=MANIFESTO_WP_SCHEMA,
    )
    try:
        corpus.require(REQUIREMENTS)  # fail fast, names the gap
        await corpus.ping()  # fail fast, auth and connectivity
        logger.info("Processing %d date(s)", len(days))
        with EditionStore(settings.database_url) as store:
            for day in days:
                try:
                    await store_cover(corpus, store, day, settings)
                except CorpusError:
                    # One bad day must not cost the rest of the run; the next
                    # lookback re-fetches it and the upsert is idempotent.
                    logger.exception("Failed to process %s", day)
                except Exception:
                    logger.exception("Unexpected failure processing %s", day)
    finally:
        await corpus.aclose()


def main() -> None:
    setup_logging()
    try:
        days = parse_dates()
        asyncio.run(run(days, load_settings()))
    except (MissingEnvironmentVariableError, InvalidDateFormatError, DateFileNotFoundError):
        logger.exception("Configuration error")
        sys.exit(1)
    except CorpusError:
        logger.exception("The archive backend could not be reached")
        sys.exit(1)
    except Exception:
        logger.exception("Unexpected error")
        sys.exit(1)
    logger.info("Successfully completed copertina processing.")


if __name__ == "__main__":
    main()
