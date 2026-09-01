"""The Postgres write side.

Deliberately outside the corpus port, which is read-only by design: where the
archive is *stored* is copertine's business, not the CMS abstraction's.
"""

import logging
from datetime import date
from types import TracebackType

import psycopg2

logger = logging.getLogger(__name__)

#: Keyed on edition_id, which is what makes re-running a lookback idempotent.
_UPSERT = """
    INSERT INTO editions (edition_id, edition_date, caption, kicker, image_filename)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (edition_id) DO UPDATE SET
        caption = EXCLUDED.caption,
        kicker = EXCLUDED.kicker,
        image_filename = EXCLUDED.image_filename,
        updated_at = now();
"""


class EditionStore:
    """One connection, one statement. Commits per row so a mid-run failure
    leaves every edition already fetched safely stored."""

    def __init__(self, database_url: str) -> None:
        self._conn = psycopg2.connect(database_url)
        self._conn.autocommit = False
        logger.info("Connected to PostgreSQL")

    def upsert(
        self,
        *,
        edition_id: str,
        edition_date: date,
        caption: str,
        kicker: str | None,
        image_filename: str,
    ) -> None:
        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    _UPSERT,
                    (edition_id, edition_date, caption, kicker, image_filename),
                )
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            logger.exception("Failed to upsert edition %s", edition_id)
            raise
        logger.info("Upserted edition %s into PostgreSQL", edition_id)

    def close(self) -> None:
        try:
            self._conn.close()
            logger.info("PostgreSQL connection closed")
        except Exception:
            logger.exception("Error closing PostgreSQL connection")

    def __enter__(self) -> "EditionStore":
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None,
                 tb: TracebackType | None) -> None:
        self.close()
