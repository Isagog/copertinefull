from datetime import date

from copertine.verify import Verdict, days_to_fix, judge, summarize

NAME = "il-manifesto_2025-10-08_onda-su-onda.jpg"


def _judge(**overrides):
    args = {"expected_filename": NAME, "expected_size": 100, "db_filename": NAME, "disk_size": 100}
    return judge(**{**args, **overrides})


def test_matching_name_and_size_is_ok():
    assert _judge() is Verdict.OK


def test_an_edition_absent_from_the_db_is_not_in_db():
    assert _judge(db_filename=None, disk_size=None) is Verdict.NOT_IN_DB


def test_a_different_name_means_a_different_headline_or_type():
    assert _judge(db_filename="il-manifesto_2025-10-08_altro.jpg") is Verdict.NAME_DIFFERS


def test_a_row_whose_file_is_gone_is_file_missing():
    assert _judge(disk_size=None) is Verdict.FILE_MISSING


def test_same_name_but_other_bytes_is_the_stale_picture_case():
    assert _judge(disk_size=99) is Verdict.SIZE_DIFFERS


def test_without_a_cms_size_the_picture_cannot_be_judged():
    assert _judge(expected_size=None) is Verdict.UNVERIFIED


def test_summarize_counts_every_verdict():
    counts = summarize([Verdict.OK, Verdict.OK, Verdict.SIZE_DIFFERS])
    assert counts[Verdict.OK] == 2
    assert counts[Verdict.SIZE_DIFFERS] == 1
    assert counts[Verdict.NOT_IN_DB] == 0


def test_days_to_fix_lists_failures_newest_first_and_skips_ok_and_unverified():
    results = {
        date(2025, 1, 1): Verdict.OK,
        date(2025, 1, 2): Verdict.SIZE_DIFFERS,
        date(2025, 1, 3): Verdict.UNVERIFIED,
        date(2025, 1, 4): Verdict.NOT_IN_DB,
    }
    assert days_to_fix(results) == [date(2025, 1, 4), date(2025, 1, 2)]
