#!/usr/bin/env python3
"""Write the date file for a backfill: editions the CMS has and the DB lacks.

    PYTHONPATH=src python tools/missing_dates.py --from 2025-01-01 --to 2025-12-31 \\
        --out missing.txt
    python src/sd2.py --datefile missing.txt

Read-only on both sides. Credentials come from the environment (or the
project-root `.secrets`), exactly as the scraper reads them: DATABASE_URL,
DIRECTUS_API_TOKEN and optionally COP_DIRECTUS_URL.

Days the CMS has no edition for (the paper skips some) are not listed, so the
output is exactly the work `sd2.py` can do. An edition that exists but has no
usable front page will still reappear on every run; the scraper logs why.
Pass --lookback-days to drop the most recent days, which the daily run already
rewrites (COP_SCRAPE_LOOKBACK_DAYS).
"""

import argparse
import asyncio
import os
import sys
from datetime import date
from pathlib import Path

import psycopg2
from corpus import EditionQuery
from corpus_directus import MANIFESTO_WP_SCHEMA, DirectusCorpus
from dotenv import load_dotenv

from copertine.backfill import format_date_file, missing_days
from copertine.config import DEFAULT_DIRECTUS_URL

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
    parser.add_argument("--out", type=Path, required=True, help="Date file to write")
    parser.add_argument("--lookback-days", type=int, default=0)
    args = parser.parse_args()
    if args.start > args.end:
        parser.error("--from must not be after --to")
    return args


async def _cms_days(start: date, end: date) -> set[date]:
    corpus = DirectusCorpus(
        base_url=os.getenv("COP_DIRECTUS_URL") or DEFAULT_DIRECTUS_URL,
        api_key=_env("DIRECTUS_API_TOKEN"),
        schema=MANIFESTO_WP_SCHEMA,
    )
    try:
        editions = await corpus.list_editions(EditionQuery(date_from=start, date_to=end))
    finally:
        await corpus.aclose()
    return {date.fromisoformat(edition.date[:10]) for edition in editions}


def _db_days(start: date, end: date) -> set[date]:
    with psycopg2.connect(_env("DATABASE_URL")) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT edition_date FROM editions WHERE edition_date BETWEEN %s AND %s",
            (start, end),
        )
        return {row[0] for row in cur.fetchall()}


def main() -> None:
    load_dotenv(dotenv_path=_SECRETS, override=True)
    args = _parse_args()
    cms = asyncio.run(_cms_days(args.start, args.end))
    db = _db_days(args.start, args.end)
    missing = missing_days(
        cms,
        db,
        today=args.end if args.lookback_days else None,
        lookback_days=args.lookback_days,
    )
    args.out.write_text(format_date_file(missing))
    print(f"CMS editions: {len(cms)}  in DB: {len(db & cms)}  missing: {len(missing)}")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
