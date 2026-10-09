"""Judging whether a stored cover is the one the CMS currently designates.

Pure functions, so the slow, network-bound loop in `tools/verify_covers.py`
stays a thin shell. The check needs no image download: the CMS reports each
file's `filesize`, and the scraper stores the bytes unmodified, so equal sizes
under equal names means the right picture is on disk.
"""

from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import date
from enum import StrEnum


class Verdict(StrEnum):
    OK = "ok"
    NOT_IN_DB = "not_in_db"
    NAME_DIFFERS = "name_differs"
    FILE_MISSING = "file_missing"
    SIZE_DIFFERS = "size_differs"
    UNVERIFIED = "unverified"


#: Verdicts that a rescrape of that day repairs. UNVERIFIED is excluded: the
#: CMS gave no size, so there is nothing to say the stored picture is wrong.
_NEEDS_FIX = frozenset(
    {Verdict.NOT_IN_DB, Verdict.NAME_DIFFERS, Verdict.FILE_MISSING, Verdict.SIZE_DIFFERS}
)


def judge(
    *,
    expected_filename: str,
    expected_size: int | None,
    db_filename: str | None,
    disk_size: int | None,
) -> Verdict:
    if db_filename is None:
        return Verdict.NOT_IN_DB
    if db_filename != expected_filename:
        return Verdict.NAME_DIFFERS
    if disk_size is None:
        return Verdict.FILE_MISSING
    if expected_size is None:
        return Verdict.UNVERIFIED
    if disk_size != expected_size:
        return Verdict.SIZE_DIFFERS
    return Verdict.OK


def summarize(verdicts: Iterable[Verdict]) -> Mapping[Verdict, int]:
    counts = Counter(verdicts)
    return {verdict: counts[verdict] for verdict in Verdict}


def days_to_fix(results: Mapping[date, Verdict]) -> list[date]:
    """Days a rescrape repairs, newest first — the `--datefile` for `sd2.py`."""
    return sorted((day for day, verdict in results.items() if verdict in _NEEDS_FIX), reverse=True)
