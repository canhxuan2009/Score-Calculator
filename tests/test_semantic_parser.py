from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from point_audit.domain import (
    DOMAIN_CONTRACT_VERSION,
    DatePrecision,
    DeltaSign,
    EventCandidate,
    EventCategory,
    EventType,
    ParseSource,
    RawCell,
    ScoringPeriod,
    SourceColumn,
    TextSpan,
    WarningCode,
)
from point_audit.parsing import (
    event_candidates_from_segments,
    parse_event_candidate,
    segment_evidence,
)

SOURCE_HASH = "d" * 64


def _candidate(raw_text: str) -> EventCandidate:
    source_cell = RawCell(
        source_file_sha256=SOURCE_HASH,
        sheet_name="Đợt 6",
        excel_row=12,
        excel_column=10,
        source_column=SourceColumn.EVIDENCE,
        source_column_name="Minh chứng",
        raw_text=raw_text,
    )
    return EventCandidate(
        person_id="student-12",
        source_cell=source_cell,
        source_span=TextSpan(start=0, end=len(raw_text)),
        candidate_index=0,
        raw_text=raw_text,
        parse_source=ParseSource.DETERMINISTIC,
    )


def _period() -> ScoringPeriod:
    return ScoringPeriod(
        period_id="dot-6-2026",
        name="Đợt 6",
        starts_on=date(2026, 2, 28),
        ends_on=date(2026, 4, 3),
        academic_year_label="2025-2026",
    )


def _parse(raw_text: str, *, period: ScoringPeriod | None = None):  # type: ignore[no-untyped-def]
    return parse_event_candidate(_candidate(raw_text), scoring_period=period)


@pytest.mark.parametrize(
    ("raw_text", "expected", "token", "sign"),
    [
        ("(+3)", Decimal("3"), "+3", DeltaSign.PLUS),
        ("(-5)", Decimal("-5"), "-5", DeltaSign.MINUS),
        ("+3", Decimal("3"), "+3", DeltaSign.PLUS),
        ("-5", Decimal("-5"), "-5", DeltaSign.MINUS),
        ("+10đ", Decimal("10"), "+10đ", DeltaSign.PLUS),
        (":+3", Decimal("3"), "+3", DeltaSign.PLUS),
        ("8 lý giữa kì+3", Decimal("3"), "+3", DeltaSign.PLUS),
        ("toán 3.5 giữa kì -5", Decimal("-5"), "-5", DeltaSign.MINUS),
        ("(+37.5)", Decimal("37.5"), "+37.5", DeltaSign.PLUS),
        ("(+37,5)", Decimal("37.5"), "+37,5", DeltaSign.PLUS),
        ("＋2", Decimal("2"), "＋2", DeltaSign.PLUS),
        ("−0,5", Decimal("-0.5"), "−0,5", DeltaSign.MINUS),
    ],
)
def test_declared_delta_formats_are_preserved(
    raw_text: str,
    expected: Decimal,
    token: str,
    sign: DeltaSign,
) -> None:
    event = _parse(raw_text)

    assert event.declared_delta == expected
    assert event.declared_delta_sign is sign
    assert event.declared_delta_span is not None
    assert event.source_cell.raw_text[
        event.declared_delta_span.start : event.declared_delta_span.end
    ] == token
    assert event.expected_delta is None
    assert event.final_delta is None
    assert event.matched_rule_id is None
    assert event.event_type is (
        EventType.BONUS if sign is DeltaSign.PLUS else EventType.PENALTY
    )


@pytest.mark.parametrize(
    ("raw_text", "expected", "token", "subject"),
    [
        ("8đ", Decimal("8"), "8", None),
        ("8.5đ", Decimal("8.5"), "8.5", None),
        ("8,5đ", Decimal("8.5"), "8,5", None),
        ("9 Toán", Decimal("9"), "9", "TOAN"),
        ("4.8 Sinh GK2", Decimal("4.8"), "4.8", "SINH"),
        ("10Sử", Decimal("10"), "10", "SU"),
        ("9.5anh16/4", Decimal("9.5"), "9.5", "ANH"),
        ("toán 3.5 giữa kì -5", Decimal("3.5"), "3.5", "TOAN"),
    ],
)
def test_academic_score_formats_are_separate_from_delta(
    raw_text: str,
    expected: Decimal,
    token: str,
    subject: str | None,
) -> None:
    event = _parse(raw_text)

    assert event.academic_score == expected
    assert event.academic_score_span is not None
    assert event.source_cell.raw_text[
        event.academic_score_span.start : event.academic_score_span.end
    ] == token
    assert event.subject == subject
    assert event.event_category is EventCategory.ACADEMIC_SCORE


def test_academic_score_declared_delta_and_date_are_independent() -> None:
    event = _parse("9đ Lí 13/3(+5)", period=_period())

    assert event.academic_score == Decimal("9")
    assert event.declared_delta == Decimal("5")
    assert event.subject == "LY"
    assert event.event_date == date(2026, 3, 13)
    assert event.date_year_inferred
    assert event.academic_score_span is not None
    assert event.declared_delta_span is not None
    assert event.date_span is not None
    assert event.source_cell.raw_text[
        event.academic_score_span.start : event.academic_score_span.end
    ] == "9"
    assert event.source_cell.raw_text[
        event.declared_delta_span.start : event.declared_delta_span.end
    ] == "+5"
    assert event.source_cell.raw_text[event.date_span.start : event.date_span.end] == "13/3"


@pytest.mark.parametrize(
    ("raw_text", "date_token", "expected_date"),
    [
        ("+3 ngày 10/3", "10/3", date(2026, 3, 10)),
        ("+3 (3/4)", "3/4", date(2026, 4, 3)),
        ("+3 ngày 31/3", "31/3", date(2026, 3, 31)),
        ("+3 31/3", "31/3", date(2026, 3, 31)),
        ("+3 10/03/2026", "10/03/2026", date(2026, 3, 10)),
    ],
)
def test_date_formats_and_period_year_resolution(
    raw_text: str,
    date_token: str,
    expected_date: date,
) -> None:
    event = _parse(raw_text, period=_period())

    assert event.date_precision is DatePrecision.FULL
    assert event.event_date == expected_date
    assert event.event_date_text == date_token
    assert event.date_span is not None
    assert event.source_cell.raw_text[event.date_span.start : event.date_span.end] == date_token
    assert event.date_year_inferred is (date_token.count("/") == 1)


def test_day_month_stays_partial_without_scoring_period() -> None:
    event = _parse("+3 ngày 10/3")

    assert event.date_precision is DatePrecision.DAY_MONTH
    assert event.event_date is None
    assert event.event_day == 10
    assert event.event_month == 3
    assert not event.date_year_inferred


@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        ("+3 ngày 31/12", date(2025, 12, 31)),
        ("+3 ngày 1/1", date(2026, 1, 1)),
    ],
)
def test_cross_year_period_infers_the_unique_year(raw_text: str, expected: date) -> None:
    period = ScoringPeriod(
        period_id="cross-year",
        name="Đợt qua năm mới",
        starts_on=date(2025, 12, 15),
        ends_on=date(2026, 1, 15),
        academic_year_label="2025-2026",
    )

    event = _parse(raw_text, period=period)

    assert event.event_date == expected
    assert event.date_year_inferred


@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        ("+3 ngày 31/12", date(2026, 12, 31)),
        ("+3 ngày 10/03/2025", date(2025, 3, 10)),
    ],
)
def test_date_outside_period_is_kept_and_warned(raw_text: str, expected: date) -> None:
    event = _parse(raw_text, period=_period())

    assert event.event_date == expected
    assert WarningCode.DATE_OUTSIDE_PERIOD in {warning.code for warning in event.warnings}
    assert event.requires_review
    assert event.final_delta is None


def test_invalid_date_is_not_repaired() -> None:
    event = _parse("+3 ngày 31/2", period=_period())
    codes = {warning.code for warning in event.warnings}

    assert event.event_date is None
    assert event.event_date_text == "31/2"
    assert event.date_precision is DatePrecision.AMBIGUOUS
    assert WarningCode.INVALID_DATE in codes
    assert WarningCode.DATE_AMBIGUOUS in codes


def test_multiple_dates_are_not_silently_resolved() -> None:
    event = _parse("+3 từ 10/3 đến 11/3", period=_period())

    assert event.event_date is None
    assert event.date_precision is DatePrecision.AMBIGUOUS
    assert WarningCode.DATE_AMBIGUOUS in {warning.code for warning in event.warnings}


@pytest.mark.parametrize(
    ("raw_text", "expected_category"),
    [
        ("9 Toán 10/3(+5)", EventCategory.ACADEMIC_SCORE),
        ("Đạt HĐTN 10/3(+3)", EventCategory.SUBJECT_ACHIEVEMENT),
        ("trực nhật tốt 10/3(+2)", EventCategory.CLASS_DUTY),
        ("tham gia cuộc thi viết 10/3(+3)", EventCategory.COMPETITION_PARTICIPATION),
        ("tham gia thi đạt giải 3 10/3(+15)", EventCategory.COMPETITION_AWARD),
        ("diễn văn nghệ mít tinh 10/3(+10)", EventCategory.PERFORMANCE),
        ("đá bóng 10/3(+10)", EventCategory.SPORTS),
        ("giúp lớp 10/3(+1)", EventCategory.POSITIVE_BEHAVIOR),
        ("vi phạm nội quy 10/3(-1)", EventCategory.NEGATIVE_BEHAVIOR),
        ("đi muộn 10/3(-2)", EventCategory.ATTENDANCE),
        ("lớp trưởng 10/3(+3)", EventCategory.ROLE),
        ("nội dung khác 10/3(+1)", EventCategory.OTHER),
    ],
)
def test_minimum_event_categories(
    raw_text: str,
    expected_category: EventCategory,
) -> None:
    assert _parse(raw_text, period=_period()).event_category is expected_category


def test_spans_remain_absolute_inside_the_raw_cell() -> None:
    raw_cell_text = "ghi chú; 9đ Lí 13/3(+5); kết thúc"
    source_cell = RawCell(
        source_file_sha256=SOURCE_HASH,
        sheet_name="Đợt 6",
        excel_row=20,
        excel_column=10,
        source_column=SourceColumn.EVIDENCE,
        source_column_name="Minh chứng",
        raw_text=raw_cell_text,
    )
    candidates = event_candidates_from_segments(
        segment_evidence(raw_cell_text),
        person_id="student-20",
        source_cell=source_cell,
    )

    event = parse_event_candidate(candidates[1], scoring_period=_period())

    assert event.event_id == candidates[1].event_id
    assert event.source_span.start > 0
    assert event.academic_score_span is not None
    assert event.subject_span is not None
    assert event.date_span is not None
    assert event.declared_delta_span is not None
    assert raw_cell_text[
        event.academic_score_span.start : event.academic_score_span.end
    ] == "9"
    assert raw_cell_text[event.subject_span.start : event.subject_span.end] == "Lí"
    assert raw_cell_text[event.date_span.start : event.date_span.end] == "13/3"
    assert raw_cell_text[
        event.declared_delta_span.start : event.declared_delta_span.end
    ] == "+5"


def test_multiple_declared_deltas_are_ambiguous_not_overwritten() -> None:
    event = _parse("gộp (+3) và (+5) ngày 10/3", period=_period())

    assert event.declared_delta is None
    assert event.expected_delta is None
    assert event.final_delta is None
    assert event.event_type is EventType.UNKNOWN
    assert WarningCode.SEGMENTATION_AMBIGUOUS in {
        warning.code for warning in event.warnings
    }


def test_delta_inside_url_is_not_parsed() -> None:
    event = _parse("xem https://example.com/?bonus=+3 ngày 10/3", period=_period())

    assert event.declared_delta is None
    assert WarningCode.MISSING_DECLARED_DELTA in {warning.code for warning in event.warnings}


def test_parser_never_applies_a_rule_or_sets_final_delta() -> None:
    event = _parse("9đ Toán 10/3(+37,5)", period=_period())

    assert event.declared_delta == Decimal("37.5")
    assert event.expected_delta is None
    assert event.final_delta is None
    assert event.matched_rule_id is None
    assert event.rule_match_confidence is None


def test_domain_contract_version_and_category_values_are_updated() -> None:
    assert DOMAIN_CONTRACT_VERSION == "0.4.0"
    assert {category.value for category in EventCategory} == {
        "ACADEMIC_SCORE",
        "SUBJECT_ACHIEVEMENT",
        "CLASS_DUTY",
        "COMPETITION_PARTICIPATION",
        "COMPETITION_AWARD",
        "PERFORMANCE",
        "SPORTS",
        "POSITIVE_BEHAVIOR",
        "NEGATIVE_BEHAVIOR",
        "ATTENDANCE",
        "ROLE",
        "OTHER",
    }
