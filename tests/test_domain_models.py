"""Unit tests for the strict Pydantic v2 domain contract."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from point_audit.domain import (
    CalculatedRowTotals,
    DatePeriodValidation,
    DatePrecision,
    DeclaredRowTotals,
    DeltaSign,
    DomainWarning,
    DuplicateMatch,
    EventCandidate,
    EventCategory,
    EventType,
    ParsedEvent,
    ParseSource,
    PersonReconciliation,
    PersonSummary,
    RawCell,
    RawWorkbookRow,
    ReviewAction,
    ReviewRecord,
    ReviewStatus,
    RuleConflict,
    RuleDefinition,
    RuleMatch,
    RuleMatchStatus,
    ScoringPeriod,
    SourceColumn,
    TextSpan,
    TimelineItem,
    TimelineItemType,
    ValidationResult,
    WarningCode,
)

SOURCE_HASH = "a" * 64
SOURCE_TEXT = "9đ Lí 13/3(+5)"


def _warning(code: WarningCode, *, blocking: bool = False) -> DomainWarning:
    return DomainWarning(code=code, message_vi=f"Cảnh báo {code.value}", blocking=blocking)


def _source_cell(raw_text: str = SOURCE_TEXT) -> RawCell:
    return RawCell(
        source_file_sha256=SOURCE_HASH,
        sheet_name="Đợt 6",
        excel_row=12,
        excel_column=10,
        source_column=SourceColumn.EVIDENCE,
        source_column_name="Minh chứng",
        raw_text=raw_text,
    )


def _candidate(**overrides: object) -> EventCandidate:
    data: dict[str, object] = {
        "person_id": "person-12",
        "source_cell": _source_cell(),
        "source_span": TextSpan(start=0, end=len(SOURCE_TEXT)),
        "candidate_index": 0,
        "raw_text": SOURCE_TEXT,
        "parse_source": ParseSource.DETERMINISTIC,
        "reported_confidence": Decimal("0.98"),
    }
    data.update(overrides)
    return EventCandidate.model_validate(data)


def _parsed_event(**overrides: object) -> ParsedEvent:
    data: dict[str, object] = {
        **_candidate().model_dump(),
        "event_type": EventType.BONUS,
        "description": "Điểm kiểm tra Lí",
        "evidence_text": SOURCE_TEXT,
        "academic_score": Decimal("9"),
        "academic_score_span": TextSpan(start=0, end=1),
        "declared_delta": Decimal("5"),
        "declared_delta_sign": DeltaSign.PLUS,
        "declared_delta_span": TextSpan(start=11, end=13),
        "event_date_text": "13/3",
        "event_date": None,
        "event_day": 13,
        "event_month": 3,
        "date_precision": DatePrecision.DAY_MONTH,
        "date_span": TextSpan(start=6, end=10),
        "matched_rule_id": "rule-academic-9",
        "expected_delta": Decimal("5"),
        "rule_match_confidence": Decimal("1"),
        "final_delta": None,
        "final_confidence": Decimal("0.96"),
        "requires_review": False,
        "review_status": ReviewStatus.UNREVIEWED,
    }
    data.update(overrides)
    return ParsedEvent.model_validate(data)


def _period() -> ScoringPeriod:
    return ScoringPeriod(
        period_id="period-2025-2026-2",
        name="Học kỳ 2",
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 5, 31),
        academic_year_label="2025-2026",
    )


def test_source_column_and_raw_row_preserve_excel_provenance() -> None:
    evidence = _source_cell()
    name = RawCell(
        source_file_sha256=SOURCE_HASH.upper(),
        sheet_name="Đợt 6",
        excel_row=12,
        excel_column=2,
        source_column=SourceColumn.FULL_NAME,
        source_column_name="Họ và tên",
        raw_text="Nguyễn Văn A",
    )

    row = RawWorkbookRow(
        source_file_sha256=SOURCE_HASH,
        sheet_name="Đợt 6",
        excel_row=12,
        cells=(name, evidence),
    )

    assert row.cells[0].source_column_name == "Họ và tên"
    assert row.cells[1].raw_text == SOURCE_TEXT
    assert row.cells[0].source_file_sha256 == SOURCE_HASH


def test_raw_row_rejects_mixed_provenance() -> None:
    wrong_row_cell = _source_cell().model_copy(update={"excel_row": 13})

    with pytest.raises(ValidationError, match="sheet and Excel row"):
        RawWorkbookRow(
            source_file_sha256=SOURCE_HASH,
            sheet_name="Đợt 6",
            excel_row=12,
            cells=(wrong_row_cell,),
        )


def test_raw_cell_preserves_formula_and_cached_value() -> None:
    cell = RawCell(
        source_file_sha256=SOURCE_HASH,
        sheet_name="Đợt 6",
        excel_row=12,
        excel_column=8,
        source_column=SourceColumn.FINAL_TOTAL,
        source_column_name="Tổng",
        raw_text="=E12+F12-G12",
        formula="=E12+F12-G12",
        cached_value_text="37.5",
    )

    assert RawCell.model_validate_json(cell.model_dump_json()) == cell


def test_raw_cell_rejects_inconsistent_formula_snapshot() -> None:
    with pytest.raises(ValidationError, match="must start"):
        RawCell(
            source_file_sha256=SOURCE_HASH,
            sheet_name="Đợt 6",
            excel_row=12,
            excel_column=8,
            source_column=SourceColumn.FINAL_TOTAL,
            source_column_name="Tổng",
            raw_text="37.5",
            formula="E12+F12-G12",
        )

    with pytest.raises(ValidationError, match="only valid for formula"):
        RawCell(
            source_file_sha256=SOURCE_HASH,
            sheet_name="Đợt 6",
            excel_row=12,
            excel_column=8,
            source_column=SourceColumn.FINAL_TOTAL,
            source_column_name="Tổng",
            raw_text="37.5",
            cached_value_text="37.5",
        )


def test_event_id_is_stable_and_position_sensitive() -> None:
    first = _candidate()
    repeated = _candidate()
    next_candidate = _candidate(candidate_index=1)

    assert first.event_id == repeated.event_id
    assert first.event_id.startswith("evt_")
    assert first.event_id != next_candidate.event_id


def test_event_id_rejects_an_arbitrary_value() -> None:
    with pytest.raises(ValidationError, match="event_id does not match"):
        _candidate(event_id="evt_not_the_source_hash")


def test_candidate_never_loses_raw_text_or_source_location() -> None:
    candidate = _candidate()

    assert candidate.raw_text == SOURCE_TEXT
    assert candidate.source_cell.sheet_name == "Đợt 6"
    assert candidate.source_cell.excel_row == 12
    assert candidate.source_cell.source_column_name == "Minh chứng"


def test_candidate_rejects_empty_or_mismatched_raw_text() -> None:
    with pytest.raises(ValidationError, match="raw_text"):
        _candidate(raw_text="")
    with pytest.raises(ValidationError, match="source cell substring"):
        _candidate(raw_text="9đ Lí")


def test_parsed_event_keeps_day_month_without_inventing_year() -> None:
    event = _parsed_event()

    assert event.date_precision is DatePrecision.DAY_MONTH
    assert event.event_day == 13
    assert event.event_month == 3
    assert event.event_date is None
    assert not event.date_year_inferred
    assert event.event_category is EventCategory.OTHER


def test_subject_and_span_must_appear_together() -> None:
    event = _parsed_event(subject="LY", subject_span=TextSpan(start=3, end=5))

    assert event.subject == "LY"
    with pytest.raises(ValidationError, match="subject and subject_span"):
        _parsed_event(subject="LY")


def test_inferred_year_requires_a_full_date() -> None:
    with pytest.raises(ValidationError, match="only valid for a FULL date"):
        _parsed_event(date_year_inferred=True)

    event = _parsed_event(
        date_precision=DatePrecision.FULL,
        event_date=date(2026, 3, 13),
        event_day=None,
        event_month=None,
        date_year_inferred=True,
    )
    assert event.date_year_inferred


def test_parsed_event_rejects_nonexistent_day_month() -> None:
    with pytest.raises(ValidationError, match="non-existent calendar date"):
        _parsed_event(event_day=31, event_month=2)


def test_full_date_uses_date_and_serializes_as_iso() -> None:
    event = _parsed_event(
        date_precision=DatePrecision.FULL,
        event_date=date(2026, 3, 13),
        event_day=None,
        event_month=None,
    )

    payload = event.model_dump_json()

    assert '"event_date":"2026-03-13"' in payload
    assert ParsedEvent.model_validate_json(payload) == event


def test_invalid_full_date_is_rejected_by_pydantic() -> None:
    data = _parsed_event().model_dump()
    data.update(
        {
            "date_precision": DatePrecision.FULL,
            "event_date": "2026-02-31",
            "event_day": None,
            "event_month": None,
        }
    )

    with pytest.raises(ValidationError):
        ParsedEvent.model_validate(data)


def test_missing_and_ambiguous_dates_are_explicit() -> None:
    missing_text = "tham gia văn nghệ(+10)"
    missing_candidate = _candidate(
        source_cell=_source_cell(missing_text),
        source_span=TextSpan(start=0, end=len(missing_text)),
        raw_text=missing_text,
    )
    missing = ParsedEvent.model_validate(
        {
            **missing_candidate.model_dump(),
            "event_type": EventType.BONUS,
            "description": "Tham gia văn nghệ",
            "evidence_text": missing_text,
            "declared_delta": Decimal("10"),
            "declared_delta_sign": DeltaSign.PLUS,
            "declared_delta_span": TextSpan(start=18, end=21),
            "date_precision": DatePrecision.MISSING,
            "final_confidence": Decimal("0.7"),
            "requires_review": True,
            "review_status": ReviewStatus.PENDING_REVIEW,
            "warnings": (_warning(WarningCode.MISSING_EVENT_DATE),),
        }
    )

    ambiguous = _parsed_event(
        date_precision=DatePrecision.AMBIGUOUS,
        event_date_text="13/3?",
        event_date=None,
        event_day=None,
        event_month=None,
        requires_review=True,
        review_status=ReviewStatus.PENDING_REVIEW,
        warnings=(_warning(WarningCode.DATE_AMBIGUOUS),),
    )

    assert missing.event_date is None
    assert ambiguous.event_date is None


def test_float_nan_and_infinity_are_rejected_for_scores() -> None:
    data = _parsed_event().model_dump()
    data["academic_score"] = float("37.5")

    with pytest.raises(ValidationError, match="float values are forbidden"):
        ParsedEvent.model_validate(data)
    with pytest.raises(ValidationError, match="finite number"):
        DeclaredRowTotals(positive_total=Decimal("NaN"))
    with pytest.raises(ValidationError, match="finite number"):
        DeclaredRowTotals(final_total=Decimal("Infinity"))


def test_decimal_comma_value_is_normalized_before_domain_and_remains_exact() -> None:
    totals = DeclaredRowTotals(positive_total="37.5", final_total=Decimal("137.5"))
    payload = totals.model_dump_json()

    assert totals.positive_total == Decimal("37.5")
    assert isinstance(totals.positive_total, Decimal)
    assert '"positive_total":"37.5"' in payload
    assert DeclaredRowTotals.model_validate_json(payload) == totals


def test_bonus_event_rejects_negative_delta() -> None:
    with pytest.raises(ValidationError, match="cannot be negative for a BONUS"):
        _parsed_event(
            declared_delta=Decimal("-5"),
            declared_delta_sign=DeltaSign.MINUS,
        )


def test_declared_sign_must_match_delta() -> None:
    with pytest.raises(ValidationError, match="PLUS sign"):
        _parsed_event(
            event_type=EventType.PENALTY,
            declared_delta=Decimal("-5"),
            declared_delta_sign=DeltaSign.PLUS,
            expected_delta=Decimal("-5"),
        )


def test_rule_conflict_is_pending_and_has_no_final_delta() -> None:
    event = _parsed_event(
        expected_delta=Decimal("3"),
        warnings=(_warning(WarningCode.RULE_CONFLICT, blocking=True),),
        requires_review=True,
        review_status=ReviewStatus.PENDING_REVIEW,
    )

    assert event.final_delta is None
    assert event.requires_review is True


def test_rule_conflict_cannot_be_silently_resolved() -> None:
    with pytest.raises(ValidationError, match="cannot receive final_delta"):
        _parsed_event(
            expected_delta=Decimal("3"),
            final_delta=Decimal("5"),
            warnings=(_warning(WarningCode.RULE_CONFLICT, blocking=True),),
            requires_review=True,
            review_status=ReviewStatus.PENDING_REVIEW,
        )


def test_ai_reported_confidence_is_distinct_from_final_confidence() -> None:
    ai_candidate = _candidate(
        parse_source=ParseSource.AI,
        reported_confidence=Decimal("0.99"),
    )
    event = _parsed_event(
        **ai_candidate.model_dump(),
        final_confidence=Decimal("0.72"),
    )

    assert event.reported_confidence == Decimal("0.99")
    assert event.final_confidence == Decimal("0.72")


def test_approved_event_requires_linked_review_information() -> None:
    with pytest.raises(ValidationError, match="review_record_id"):
        _parsed_event(
            final_delta=Decimal("5"),
            review_status=ReviewStatus.APPROVED,
        )

    approved = _parsed_event(
        final_delta=Decimal("5"),
        review_status=ReviewStatus.APPROVED,
        review_record_id="review-1",
    )
    assert approved.final_delta == Decimal("5")


def test_review_record_requires_complete_audit_metadata() -> None:
    with pytest.raises(ValidationError, match="reviewer_id"):
        ReviewRecord(
            review_id="review-1",
            event_id=_candidate().event_id,
            status=ReviewStatus.APPROVED,
            action=ReviewAction.USE_DECLARED,
            final_delta=Decimal("5"),
        )

    review = ReviewRecord(
        review_id="review-1",
        event_id=_candidate().event_id,
        status=ReviewStatus.APPROVED,
        action=ReviewAction.USE_DECLARED,
        reviewer_id="teacher-1",
        reviewed_at=datetime(2026, 3, 20, 8, 30, tzinfo=UTC),
        reason="Đã đối chiếu minh chứng gốc",
        final_delta=Decimal("5"),
    )

    assert ReviewRecord.model_validate_json(review.model_dump_json()) == review


def test_review_timestamp_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        ReviewRecord(
            review_id="review-1",
            event_id=_candidate().event_id,
            status=ReviewStatus.REJECTED,
            action=ReviewAction.REJECT_EVENT,
            reviewer_id="teacher-1",
            reviewed_at=datetime(2026, 3, 20, 8, 30),
            reason="Minh chứng bị lặp",
        )


def test_validation_result_requires_explanations_and_review() -> None:
    with pytest.raises(ValidationError, match="explain"):
        ValidationResult(is_valid=False, requires_review=True)
    with pytest.raises(ValidationError, match="blocking warnings"):
        ValidationResult(
            is_valid=True,
            warnings=(_warning(WarningCode.UNRESOLVED_EVENT, blocking=True),),
        )

    result = ValidationResult(
        is_valid=False,
        errors=("Không xác định được ngày",),
        requires_review=True,
    )
    assert result.requires_review is True


def test_duplicate_match_never_auto_removes_an_event() -> None:
    match = DuplicateMatch(
        event_id=_candidate().event_id,
        duplicate_event_id=_candidate(candidate_index=1).event_id,
        similarity_score=Decimal("0.92"),
        reasons=("Cùng người, ngày và nội dung chuẩn hóa",),
    )

    assert match.requires_review is True
    with pytest.raises(ValidationError, match="two different events"):
        DuplicateMatch(
            event_id=match.event_id,
            duplicate_event_id=match.event_id,
            similarity_score=Decimal("1"),
            reasons=("Giống nhau",),
        )


def test_scoring_period_and_day_month_period_validation() -> None:
    validation = DatePeriodValidation(
        event_id=_candidate().event_id,
        scoring_period=_period(),
        date_precision=DatePrecision.DAY_MONTH,
        event_day=13,
        event_month=3,
        candidate_dates=(date(2026, 3, 13),),
        is_within_period=True,
    )

    assert validation.event_date is None
    assert validation.candidate_dates == (date(2026, 3, 13),)

    with pytest.raises(ValidationError, match="must not precede"):
        ScoringPeriod(
            period_id="bad",
            name="Sai",
            starts_on=date(2026, 5, 31),
            ends_on=date(2026, 1, 1),
            academic_year_label="2025-2026",
        )


def test_full_date_outside_period_requires_warning() -> None:
    with pytest.raises(ValidationError, match="DATE_OUTSIDE_PERIOD"):
        DatePeriodValidation(
            event_id=_candidate().event_id,
            scoring_period=_period(),
            date_precision=DatePrecision.FULL,
            event_date=date(2025, 12, 31),
            is_within_period=False,
        )


def test_calculated_totals_enforce_formula_but_declared_totals_do_not() -> None:
    declared = DeclaredRowTotals(
        base_score=Decimal("100"),
        positive_total=Decimal("5"),
        negative_total=Decimal("2"),
        final_total=Decimal("999"),
    )
    assert declared.final_total == Decimal("999")

    with pytest.raises(ValidationError, match=r"base \+ positive - negative"):
        CalculatedRowTotals(
            base_score=Decimal("100"),
            positive_total=Decimal("5"),
            negative_total=Decimal("2"),
            final_total=Decimal("104"),
        )


def test_person_reconciliation_computes_exact_decimal_differences() -> None:
    declared = DeclaredRowTotals(
        base_score=Decimal("100"),
        positive_total=Decimal("5"),
        negative_total=Decimal("4"),
        final_total=Decimal("101"),
    )
    calculated = CalculatedRowTotals(
        base_score=Decimal("100"),
        positive_total=Decimal("8"),
        negative_total=Decimal("3"),
        final_total=Decimal("105"),
    )

    reconciliation = PersonReconciliation.from_totals(
        declared=declared,
        calculated=calculated,
        unresolved_event_count=2,
    )

    assert reconciliation.declared_positive_total == Decimal("5")
    assert reconciliation.declared_negative_total == Decimal("4")
    assert reconciliation.declared_final_total == Decimal("101")
    assert reconciliation.calculated_positive_total == Decimal("8")
    assert reconciliation.calculated_negative_total == Decimal("3")
    assert reconciliation.calculated_final_total == Decimal("105")
    assert reconciliation.positive_difference == Decimal("3")
    assert reconciliation.negative_difference == Decimal("-1")
    assert reconciliation.final_difference == Decimal("4")
    assert reconciliation.unresolved_event_count == 2


def test_rule_definition_match_and_conflict_states() -> None:
    rule = RuleDefinition(
        rule_id="rule-academic-9",
        version="1.0.0",
        name="Điểm kiểm tra từ 9",
        event_type=EventType.BONUS,
        expected_delta=Decimal("5"),
        priority=10,
        academic_score_min=Decimal("9"),
        description_keywords=("điểm", "lí"),
    )
    match = RuleMatch(
        event_id=_candidate().event_id,
        status=RuleMatchStatus.ONE_MATCH,
        matched_rule_id=rule.rule_id,
        candidate_rule_ids=(rule.rule_id,),
        expected_delta=rule.expected_delta,
        confidence=Decimal("1"),
        trace=("academic_score >= 9",),
    )
    conflict = RuleConflict(
        event_id=match.event_id,
        rule_id=rule.rule_id,
        declared_delta=Decimal("3"),
        expected_delta=Decimal("5"),
    )

    assert match.status is RuleMatchStatus.ONE_MATCH
    assert conflict.resolved is False

    with pytest.raises(ValidationError, match="different"):
        RuleConflict(
            event_id=match.event_id,
            rule_id=rule.rule_id,
            declared_delta=Decimal("5"),
            expected_delta=Decimal("5"),
        )


def test_rule_definition_rejects_wrong_delta_direction() -> None:
    with pytest.raises(ValidationError, match="cannot be negative for a BONUS"):
        RuleDefinition(
            rule_id="bad-rule",
            version="1",
            name="Sai dấu",
            event_type=EventType.BONUS,
            expected_delta=Decimal("-5"),
            priority=1,
        )


def test_rule_match_rejects_ambiguous_selection() -> None:
    with pytest.raises(ValidationError, match="cannot select"):
        RuleMatch(
            event_id=_candidate().event_id,
            status=RuleMatchStatus.AMBIGUOUS_MATCH,
            matched_rule_id="rule-1",
            candidate_rule_ids=("rule-1", "rule-2"),
            expected_delta=Decimal("5"),
        )


def test_timeline_and_person_summary_are_auditable() -> None:
    reconciliation = PersonReconciliation(
        declared_positive_total=Decimal("5"),
        declared_negative_total=Decimal("0"),
        declared_final_total=Decimal("105"),
        calculated_positive_total=Decimal("5"),
        calculated_negative_total=Decimal("0"),
        calculated_final_total=Decimal("105"),
        unresolved_event_count=0,
    )
    summary = PersonSummary(
        person_id="person-12",
        full_name="Nguyễn Văn A",
        sheet_name="Đợt 6",
        excel_row=12,
        scoring_period_id=_period().period_id,
        reconciliation=reconciliation,
        event_ids=(_candidate().event_id,),
        requires_review=False,
    )
    item = TimelineItem(
        item_id="timeline-1",
        person_id=summary.person_id,
        event_id=summary.event_ids[0],
        item_type=TimelineItemType.PARSED,
        occurred_at=datetime(2026, 3, 13, 9, tzinfo=UTC),
        description="Đã phân tích sự kiện bằng Python",
        actor_id="point-audit",
    )

    assert summary.excel_row == 12
    assert item.event_id == summary.event_ids[0]
