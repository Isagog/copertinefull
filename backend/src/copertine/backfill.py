"""Which editions the CMS has that the archive lacks.

Pure set arithmetic, so the one-off tool in `tools/missing_dates.py` can be a
thin shell around I/O and this stays testable without a CMS or a database.
"""

from collections.abc import Iterable
from datetime import date, timedelta


def missing_days(
    cms_days: Iterable[date],
    db_days: Iterable[date],
    *,
    today: date | None = None,
    lookback_days: int = 0,
) -> list[date]:
    """CMS days absent from the database, newest first.

    The daily run rewrites the last `lookback_days` days (COP_SCRAPE_LOOKBACK_DAYS),
    so when `today` is given those days are left out: listing them would only
    duplicate work the schedule already does.
    """
    present = set(db_days)
    cutoff = today - timedelta(days=lookback_days) if today else None
    return sorted(
        (d for d in set(cms_days) if d not in present and (cutoff is None or d <= cutoff)),
        reverse=True,
    )


def format_date_file(days: Iterable[date]) -> str:
    """The `--datefile` format of `sd2.py`: one YYYY-MM-DD per line."""
    return "".join(f"{day.isoformat()}\n" for day in days)
