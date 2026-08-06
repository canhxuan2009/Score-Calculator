from __future__ import annotations

import pytest

from point_audit.domain import ParseSource, RawCell, SourceColumn, WarningCode
from point_audit.parsing import (
    event_candidates_from_segments,
    is_decimal_comma,
    segment_evidence,
    starts_new_event,
)


def _texts(raw_text: str) -> list[str]:
    return [segment.raw_text for segment in segment_evidence(raw_text).segments]


@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        (
            "+5 9đ toán 10/5, -2 đi muộn 11/5",
            ["+5 9đ toán 10/5", "-2 đi muộn 11/5"],
        ),
        (
            "+2,5 trực nhật tốt; +1 giúp lớp",
            ["+2,5 trực nhật tốt", "+1 giúp lớp"],
        ),
        ("+5 toán 9đ", ["+5 toán 9đ"]),
        ("-1 vi phạm; -0,5 quên khăn", ["-1 vi phạm", "-0,5 quên khăn"]),
        ("+3 ngày 10/5", ["+3 ngày 10/5"]),
        (
            "Đạt HĐTN 10/3(+3), 9đ Lí 13/3(+5), 4.8đ Toán GK2(-5)",
            ["Đạt HĐTN 10/3(+3)", "9đ Lí 13/3(+5)", "4.8đ Toán GK2(-5)"],
        ),
        (
            "8 lý giữa kì+3 , đạt HDTN 27/3 +3, đá bóng+10, kéo co(+5)",
            ["8 lý giữa kì+3", "đạt HDTN 27/3 +3", "đá bóng+10", "kéo co(+5)"],
        ),
        (
            "8đ lý :+3 (5/3) ,đạt hđtn: +3 (14/3) ,+10đ (diễn văn nghệ)",
            ["8đ lý :+3 (5/3)", "đạt hđtn: +3 (14/3)", "+10đ (diễn văn nghệ)"],
        ),
        (
            "3.2 Lý GK2 (-5), 3.1 Hoá GK2 (-5), 4.3Sinh GK2 (-5),4 Tin GK2 (-5)",
            [
                "3.2 Lý GK2 (-5)",
                "3.1 Hoá GK2 (-5)",
                "4.3Sinh GK2 (-5)",
                "4 Tin GK2 (-5)",
            ],
        ),
        (
            "9 Sử 7/4 (+5) 10 Hóa 10/4 (+5) 8 Toán 17/4 (+3)",
            ["9 Sử 7/4 (+5)", "10 Hóa 10/4 (+5)", "8 Toán 17/4 (+3)"],
        ),
        ("8,5đ toán (+5)", ["8,5đ toán (+5)"]),
        ("37,5 điểm thi chạy (+3)", ["37,5 điểm thi chạy (+3)"]),
        ("ngày 10/3 tham gia lao động (+2)", ["ngày 10/3 tham gia lao động (+2)"]),
        ("thi Văn, Sử cấp trường (+10)", ["thi Văn, Sử cấp trường (+10)"]),
        (
            "tham gia văn nghệ giải 3 và diễn văn nghệ ở trường (+25)",
            ["tham gia văn nghệ giải 3 và diễn văn nghệ ở trường (+25)"],
        ),
        ("   +1 trực nhật tốt   ", ["+1 trực nhật tốt"]),
        ("+1 tốt\n-1 vi phạm", ["+1 tốt", "-1 vi phạm"]),
        ("+1 tốt\r\n-1 vi phạm", ["+1 tốt", "-1 vi phạm"]),
        ("＋2 giúp lớp; －1 vi phạm", ["＋2 giúp lớp", "－1 vi phạm"]),
        ("﹢2 giúp lớp\n−1 vi phạm", ["﹢2 giúp lớp", "−1 vi phạm"]),
        ("tham gia văn nghệ (+10)", ["tham gia văn nghệ (+10)"]),
        (
            "Xem https://example.com/a,b?x=+3 rồi xác nhận",
            ["Xem https://example.com/a,b?x=+3 rồi xác nhận"],
        ),
        (
            "Xem https://example.com/a;b?x=1,2 (+3)",
            ["Xem https://example.com/a;b?x=1,2 (+3)"],
        ),
        (
            "Xem https://example.com/a,b?x=1,2; +1 xác nhận",
            ["Xem https://example.com/a,b?x=1,2", "+1 xác nhận"],
        ),
        ("+1 tốt;;,   -1 xấu", ["+1 tốt", "-1 xấu"]),
        ("+1 tốt,,   +2 giúp lớp", ["+1 tốt", "+2 giúp lớp"]),
        (";; +1 tốt", ["+1 tốt"]),
        ("+1 tốt;;  ", ["+1 tốt"]),
        ("Không hiểu đoạn này", ["Không hiểu đoạn này"]),
        ("", []),
        ("   \t", []),
        ("nội dung, chưa có dấu hiệu điểm mới", ["nội dung, chưa có dấu hiệu điểm mới"]),
        ("tham gia bóng đá, kéo co (+10)", ["tham gia bóng đá, kéo co (+10)"]),
        ("ghi chú, đạt HĐTN (+3)", ["ghi chú, đạt HĐTN (+3)"]),
        ("+1 tốt -2 đi muộn", ["+1 tốt", "-2 đi muộn"]),
        ("đá bóng+10 kéo co(+5)", ["đá bóng+10", "kéo co(+5)"]),
        ("8 lý giữa kì+3 9 toán cuối kì+5", ["8 lý giữa kì+3", "9 toán cuối kì+5"]),
        ("8 lý :+3 (5/3)", ["8 lý :+3 (5/3)"]),
        ("4.8đ Toán GK2 (-5)", ["4.8đ Toán GK2 (-5)"]),
        ("+1 tốt;\n\n  -2 xấu", ["+1 tốt", "-2 xấu"]),
        ("+1 tốt, +2 giúp lớp, -0,5 quên khăn", ["+1 tốt", "+2 giúp lớp", "-0,5 quên khăn"]),
        ("10/5 toán 9đ (+5), 11/5 lý 8đ (+3)", ["10/5 toán 9đ (+5)", "11/5 lý 8đ (+3)"]),
    ],
)
def test_segment_examples(raw_text: str, expected: list[str]) -> None:
    assert _texts(raw_text) == expected


def test_exact_spans_delimiters_and_round_trip() -> None:
    raw_text = "  +1 tốt  ,   -2 xấu\n+3 khác  "

    result = segment_evidence(raw_text)

    assert result.leading_text == "  "
    assert [segment.delimiter_after for segment in result.segments] == ["  ,   ", "\n", "  "]
    assert result.leading_text + "".join(
        segment.raw_text + segment.delimiter_after for segment in result.segments
    ) == raw_text
    assert all(
        raw_text[segment.source_span.start : segment.source_span.end] == segment.raw_text
        for segment in result.segments
    )


def test_decimal_comma_is_lexical_not_a_boundary() -> None:
    raw_text = "+2,5 tốt, +1 khác"

    assert is_decimal_comma(raw_text, raw_text.index(","))
    assert not is_decimal_comma(raw_text, raw_text.rindex(","))


@pytest.mark.parametrize(
    ("raw_text", "position"),
    [
        ("+1 giúp lớp", 0),
        ("−1 vi phạm", 0),
        ("9đ Toán (+5)", 0),
        ("Đạt HĐTN (+3)", 0),
        ("đá bóng (+10)", 0),
        ("10/5 toán 9đ (+5)", 0),
    ],
)
def test_recognized_event_starts(raw_text: str, position: int) -> None:
    assert starts_new_event(raw_text, position)


def test_ambiguous_comma_is_preserved_and_warned() -> None:
    result = segment_evidence("tham gia bóng đá, kéo co (+10)")

    assert len(result.segments) == 1
    assert result.is_ambiguous
    assert result.warnings[0].code is WarningCode.SEGMENTATION_AMBIGUOUS
    assert result.warnings[0].blocking
    assert result.segments[0].warnings == result.warnings


def test_strong_delimiter_inside_parentheses_is_preserved_and_warned() -> None:
    result = segment_evidence("tham gia (Văn; Sử) cấp trường (+10)")

    assert _texts(result.raw_text) == ["tham gia (Văn; Sử) cấp trường (+10)"]
    assert result.is_ambiguous


def test_unclosed_parenthesis_is_preserved_and_warned() -> None:
    result = segment_evidence("tham gia văn nghệ (+10")

    assert _texts(result.raw_text) == ["tham gia văn nghệ (+10"]
    assert result.is_ambiguous


def test_result_is_deterministic() -> None:
    raw_text = "8,5 Toán (+5), đạt HĐTN (+3); -1 đi muộn"

    assert segment_evidence(raw_text) == segment_evidence(raw_text)


def test_unknown_text_is_never_dropped() -> None:
    raw_text = "??? nội dung chưa hiểu ???; +1 giúp lớp"
    result = segment_evidence(raw_text)

    assert [segment.raw_text for segment in result.segments] == [
        "??? nội dung chưa hiểu ???",
        "+1 giúp lớp",
    ]
    assert "".join(
        [result.leading_text]
        + [segment.raw_text + segment.delimiter_after for segment in result.segments]
    ) == raw_text


def test_event_candidates_keep_domain_provenance() -> None:
    raw_text = "+1 giúp lớp; -0,5 quên khăn"
    source_cell = RawCell(
        source_file_sha256="a" * 64,
        sheet_name="Đợt 6",
        excel_row=12,
        excel_column=10,
        source_column=SourceColumn.EVIDENCE,
        source_column_name="Minh chứng",
        raw_text=raw_text,
    )

    candidates = event_candidates_from_segments(
        segment_evidence(raw_text),
        person_id="student-12",
        source_cell=source_cell,
    )

    assert len(candidates) == 2
    assert [candidate.candidate_index for candidate in candidates] == [0, 1]
    assert all(candidate.parse_source is ParseSource.DETERMINISTIC for candidate in candidates)
    assert all(candidate.reported_confidence is None for candidate in candidates)
    assert all(
        raw_text[candidate.source_span.start : candidate.source_span.end] == candidate.raw_text
        for candidate in candidates
    )
    assert candidates[0].event_id != candidates[1].event_id


def test_ambiguous_candidate_has_warning_without_invented_confidence() -> None:
    raw_text = "tham gia bóng đá, kéo co (+10)"
    source_cell = RawCell(
        source_file_sha256="b" * 64,
        sheet_name="Đợt 6",
        excel_row=13,
        excel_column=10,
        source_column=SourceColumn.EVIDENCE,
        source_column_name="Minh chứng",
        raw_text=raw_text,
    )

    (candidate,) = event_candidates_from_segments(
        segment_evidence(raw_text), person_id="student-13", source_cell=source_cell
    )

    assert candidate.reported_confidence is None
    assert candidate.warnings[0].code is WarningCode.SEGMENTATION_AMBIGUOUS


def test_candidate_conversion_rejects_a_different_source_text() -> None:
    result = segment_evidence("+1 giúp lớp")
    source_cell = RawCell(
        source_file_sha256="c" * 64,
        sheet_name="Đợt 6",
        excel_row=14,
        excel_column=10,
        source_column=SourceColumn.EVIDENCE,
        source_column_name="Minh chứng",
        raw_text="+2 nội dung khác",
    )

    with pytest.raises(ValueError, match="must match"):
        event_candidates_from_segments(result, person_id="student-14", source_cell=source_cell)


def test_non_string_input_is_rejected() -> None:
    with pytest.raises(TypeError, match="must be a string"):
        segment_evidence(123)  # type: ignore[arg-type]
