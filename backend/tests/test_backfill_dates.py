from datetime import date

from copertine.backfill import format_date_file, missing_days


def test_missing_days_are_cms_days_absent_from_the_db():
    cms = {date(2025, 10, 8), date(2025, 10, 9), date(2025, 10, 10)}
    db = {date(2025, 10, 9)}
    assert missing_days(cms, db) == [date(2025, 10, 10), date(2025, 10, 8)]


def test_days_only_in_the_db_are_not_listed():
    assert missing_days({date(2025, 1, 2)}, {date(2025, 1, 2), date(2025, 1, 3)}) == []


def test_nothing_missing_is_an_empty_list():
    assert missing_days(set(), set()) == []


def test_the_lookback_window_is_excluded_because_the_daily_run_rewrites_it():
    cms = {date(2026, 10, 8), date(2026, 10, 7), date(2026, 10, 1)}
    today = date(2026, 10, 8)
    assert missing_days(cms, set(), today=today, lookback_days=3) == [date(2026, 10, 1)]


def test_date_file_is_one_iso_day_per_line_with_trailing_newline():
    assert format_date_file([date(2025, 10, 10), date(2025, 10, 8)]) == "2025-10-10\n2025-10-08\n"


def test_empty_date_file_is_empty_text():
    assert format_date_file([]) == ""
