#!/usr/bin/env python3
"""Check that stored covers are the ones the CMS designates. Read-only.

    python tools/verify_covers.py --from 2021-10-08 --to 2026-10-08 \\
        --out to-fix.txt

Per edition: one cover request to the CMS (plus a few paged listing requests
up front), spaced `--delay` seconds apart, 1.0 by default, so five years is
~30 minutes at about one request a second. No image is downloaded: the CMS's
`filesize` is compared with the size of the file on disk, and the expected
filename with the one in the database. Run it where the images directory is
mounted (the scraper container). Stops early after `--max-errors` consecutive
CMS failures rather than hammering a struggling server.

`--out` is a date file for `python src/sd2.py --datefile`; it is rewritten as
the run progresses, so an interrupted run still leaves a usable list.
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import date
from pathlib import Path

import psycopg2
from corpus import (
    CorpusError,
    DocumentNotFound,
    EditionQuery,
    InvalidDocument,
)
from corpus_directus import MANIFESTO_WP_SCHEMA, DirectusCorpus
from dotenv import load_dotenv

from copertine.backfill import format_date_file
from copertine.config import DEFAULT_DIRECTUS_URL, setup_logging
from copertine.naming import image_filename
from copertine.verify import Verdict, days_to_fix, judge, summarize

logger = logging.getLogger("copertine.verify")

_SECRETS = Path(__file__).parents[2] / ".secrets"


def _env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.exit(f"Environment variable '{name}' must be set.")
    return value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--from", dest="start", type=date.fromisoformat, required=True)
    parser.add_argument("--to", dest="end", type=date.fromisoformat, required=True)
    parser.add_argument("--out", type=Path, required=True, help="Date file of days to fix")
    parser.add_argument("--images-dir", type=Path, default=None)
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between CMS requests")
    parser.add_argument("--max-errors", type=int, default=5)
    args = parser.parse_args()
    if args.start > args.end:
        parser.error("--from must not be after --to")
    if args.delay < 0:
        parser.error("--delay must not be negative")
    return args


def _db_filenames(start: date, end: date) -> dict[date, str]:
    with psycopg2.connect(_env("DATABASE_URL")) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT edition_date, image_filename FROM editions"
            " WHERE edition_date BETWEEN %s AND %s",
            (start, end),
        )
        return {row[0]: row[1] for row in cur.fetchall()}


def _disk_size(images_dir: Path, filename: str | None) -> int | None:
    if filename is None:
        return None
    path = images_dir / filename
    return path.stat().st_size if path.is_file() else None


async def _verify(args: argparse.Namespace, images_dir: Path) -> dict[date, Verdict]:
    corpus = DirectusCorpus(
        base_url=os.getenv("COP_DIRECTUS_URL") or DEFAULT_DIRECTUS_URL,
        api_key=_env("DIRECTUS_API_TOKEN"),
        schema=MANIFESTO_WP_SCHEMA,
    )
    db = _db_filenames(args.start, args.end)
    results: dict[date, Verdict] = {}
    consecutive_errors = 0
    try:
        editions = await corpus.list_editions(
            EditionQuery(date_from=args.start, date_to=args.end)
        )
        logger.info("%d CMS editions to check", len(editions))
        for index, edition in enumerate(sorted(editions, key=lambda e: e.date, reverse=True), 1):
            day = date.fromisoformat(edition.date[:10])
            await asyncio.sleep(args.delay)
            try:
                cover = await corpus.get_edition_cover(edition.id)
            except (DocumentNotFound, InvalidDocument) as err:
                # No usable cover in the CMS: nothing the scraper could store.
                logger.info("%s: no usable cover (%s)", day, err)
                consecutive_errors = 0
                continue
            except CorpusError:
                consecutive_errors += 1
                logger.exception("%s: CMS request failed", day)
                if consecutive_errors >= args.max_errors:
                    logger.exception("%d failures in a row — stopping", consecutive_errors)
                    break
                continue
            consecutive_errors = 0
            if cover.image is None:
                continue
            stored = db.get(day)
            results[day] = judge(
                expected_filename=image_filename(day, cover.headline, cover.image),
                expected_size=cover.image.size,
                db_filename=stored,
                disk_size=_disk_size(images_dir, stored),
            )
            if results[day] is not Verdict.OK:
                logger.warning("%s: %s", day, results[day].value)
            args.out.write_text(format_date_file(days_to_fix(results)))
            if index % 100 == 0:
                logger.info("%d/%d checked", index, len(editions))
    finally:
        await corpus.aclose()
    return results


def main() -> None:
    setup_logging()
    load_dotenv(dotenv_path=_SECRETS, override=True)
    args = _parse_args()
    images_dir = args.images_dir or Path(os.getenv("COP_IMAGES_DIR") or _SECRETS.parent / "images")
    results = asyncio.run(_verify(args, images_dir))
    args.out.write_text(format_date_file(days_to_fix(results)))
    print(f"Checked {len(results)} editions")
    for verdict, count in summarize(results.values()).items():
        print(f"  {verdict.value:13} {count}")
    print(f"Wrote {args.out} ({len(days_to_fix(results))} days to fix)")


if __name__ == "__main__":
    main()
