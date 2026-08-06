"""Pydantic v2 domain models for auditable point processing."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Self

from pydantic import Field, field_validator, model_validator

from point_audit.domain.enums import (
    DatePrecision,
    DeltaSign,
    EventType,
    ParseSource,
    ReviewAction,
    ReviewStatus,
    RuleMatchStatus,
    SourceColumn,
    TimelineItemType,
    WarningCode,
)
from point_audit.domain.types import (
    ConfidenceDecimal,
    DomainModel,
    FiniteDecimal,
    NonNegativeDecimal,
    TextSpan,
    build_event_id,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _require_nonblank(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


def _warning_codes(warnings: tuple[DomainWarning, ...]) -> set[WarningCode]:
    return {warning.code for warning in warnings}


def _validate_timezone(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def _validate_delta_direction(event_type: EventType, delta: Decimal, field_name: str) -> None:
    if event_type is EventType.BONUS and delta < 0:
        raise ValueError(f"{field_name} cannot be negative for a BONUS event")
    if event_type is EventType.PENALTY and delta > 0:
        raise ValueError(f"{field_name} cannot be positive for a PENALTY event")
    if event_type is EventType.INFORMATIONAL:
        raise ValueError(f"{field_name} must be absent for an INFORMATIONAL event")


class DomainWarning(DomainModel):
    """Machine-readable warning with a Vietnamese user-facing message."""

    code: WarningCode
    message_vi: str
    blocking: bool = False

    @field_validator("message_vi")
    @classmethod
    def validate_message(cls, value: str) -> str:
        return _require_nonblank(value, "message_vi")


class RawCell(DomainModel):
    """Lossless text representation of one physical Excel cell."""

    source_file_sha256: str
    sheet_name: str
    excel_row: int = Field(ge=1)
    excel_column: int = Field(ge=1)
    source_column: SourceColumn
    source_column_name: str
    raw_text: str
    formula: str | None = None
    cached_value_text: str | None = None

    @field_validator("source_file_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        normalized = value.lower()
        if _SHA256_PATTERN.fullmatch(normalized) is None:
            raise ValueError("source_file_sha256 must be a 64-character hexadecimal SHA-256")
        return normalized

    @field_validator("sheet_name", "source_column_name")
    @classmethod
    def validate_names(cls, value: str) -> str:
        return _require_nonblank(value, "source name")

    @model_validator(mode="after")
    def validate_formula_snapshot(self) -> Self:
        if self.formula is not None:
            if not self.formula.startswith("="):
                raise ValueError("formula must start with '='")
            if self.raw_text != self.formula:
                raise ValueError("raw_text must preserve the formula text")
        elif self.cached_value_text is not None:
            raise ValueError("cached_value_text is only valid for formula cells")
        return self


class RawWorkbookRow(DomainModel):
    """One source workbook row with physical provenance preserved."""

    source_file_sha256: str
    sheet_name: str
    excel_row: int = Field(ge=1)
    cells: tuple[RawCell, ...] = Field(min_length=1)

    @field_validator("source_file_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        normalized = value.lower()
        if _SHA256_PATTERN.fullmatch(normalized) is None:
            raise ValueError("source_file_sha256 must be a 64-character hexadecimal SHA-256")
        return normalized

    @field_validator("sheet_name")
    @classmethod
    def validate_sheet_name(cls, value: str) -> str:
        return _require_nonblank(value, "sheet_name")

    @model_validator(mode="after")
    def validate_cell_provenance(self) -> Self:
        seen_columns: set[int] = set()
        for cell in self.cells:
            if cell.source_file_sha256 != self.source_file_sha256:
                raise ValueError("all cells must reference the row's source file hash")
            if cell.sheet_name != self.sheet_name or cell.excel_row != self.excel_row:
                raise ValueError("all cells must reference the row's sheet and Excel row")
            if cell.excel_column in seen_columns:
                raise ValueError("a raw workbook row cannot contain duplicate Excel columns")
            seen_columns.add(cell.excel_column)
        return self


class EventCandidate(DomainModel):
    """A source-backed event segment before semantic validation."""

    event_id: str = ""
    person_id: str
    source_cell: RawCell
    source_span: TextSpan
    candidate_index: int = Field(ge=0)
    raw_text: str
    parse_source: ParseSource
    reported_confidence: ConfidenceDecimal | None = None
    warnings: tuple[DomainWarning, ...] = ()

    @field_validator("person_id")
    @classmethod
    def validate_person_id(cls, value: str) -> str:
        return _require_nonblank(value, "person_id")

    @model_validator(mode="after")
    def validate_source_and_id(self) -> Self:
        if not self.raw_text:
            raise ValueError("raw_text must not be empty")
        if self.source_cell.source_column is not SourceColumn.EVIDENCE:
            raise ValueError("event candidates must originate from the EVIDENCE column")
        if self.source_span.end > len(self.source_cell.raw_text):
            raise ValueError("source_span exceeds source cell raw_text")
        source_substring = self.source_cell.raw_text[
            self.source_span.start : self.source_span.end
        ]
        if source_substring != self.raw_text:
            raise ValueError("raw_text must exactly match the source cell substring")

        expected_id = build_event_id(
            source_file_sha256=self.source_cell.source_file_sha256,
            sheet_name=self.source_cell.sheet_name,
            excel_row=self.source_cell.excel_row,
            excel_column=self.source_cell.excel_column,
            source_column_name=self.source_cell.source_column_name,
            source_span=self.source_span,
            candidate_index=self.candidate_index,
            raw_text=self.raw_text,
        )
        if self.event_id and self.event_id != expected_id:
            raise ValueError("event_id does not match the stable source identity")
        if not self.event_id:
            object.__setattr__(self, "event_id", expected_id)
        return self


class ParsedEvent(EventCandidate):
    """Validated semantic event with separated scores, date and review state."""

    event_type: EventType
    description: str
    evidence_text: str
    academic_score: FiniteDecimal | None = None
    declared_delta: FiniteDecimal | None = None
    expected_delta: FiniteDecimal | None = None
    final_delta: FiniteDecimal | None = None
    declared_delta_sign: DeltaSign | None = None
    academic_score_span: TextSpan | None = None
    declared_delta_span: TextSpan | None = None
    date_span: TextSpan | None = None
    event_date_text: str | None = None
    event_date: date | None = None
    event_day: int | None = Field(default=None, ge=1, le=31)
    event_month: int | None = Field(default=None, ge=1, le=12)
    date_precision: DatePrecision
    matched_rule_id: str | None = None
    rule_match_confidence: ConfidenceDecimal | None = None
    final_confidence: ConfidenceDecimal
    requires_review: bool
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    review_record_id: str | None = None

    @field_validator("description", "evidence_text")
    @classmethod
    def validate_event_text(cls, value: str) -> str:
        return _require_nonblank(value, "event text")

    @model_validator(mode="after")
    def validate_parsed_state(self) -> Self:
        if self.evidence_text not in self.raw_text:
            raise ValueError("evidence_text must be preserved within raw_text")
        self._validate_optional_span(self.academic_score_span, "academic_score_span")
        self._validate_optional_span(self.declared_delta_span, "declared_delta_span")
        self._validate_optional_span(self.date_span, "date_span")
        self._validate_score_spans()
        self._validate_date_state()
        self._validate_rule_state()
        self._validate_delta_state()
        self._validate_review_state()
        return self

    def _validate_optional_span(self, span: TextSpan | None, field_name: str) -> None:
        if span is None:
            return
        if span.start < self.source_span.start or span.end > self.source_span.end:
            raise ValueError(f"{field_name} must be contained within source_span")

    def _validate_score_spans(self) -> None:
        if (self.academic_score is None) != (self.academic_score_span is None):
            raise ValueError("academic_score and academic_score_span must appear together")
        declared_parts = (
            self.declared_delta is not None,
            self.declared_delta_span is not None,
            self.declared_delta_sign is not None,
        )
        if len(set(declared_parts)) != 1:
            raise ValueError(
                "declared_delta, declared_delta_span and declared_delta_sign must appear together"
            )
        if self.declared_delta is not None and self.declared_delta_sign is not None:
            if self.declared_delta_sign is DeltaSign.PLUS and self.declared_delta < 0:
                raise ValueError("PLUS sign cannot accompany a negative declared_delta")
            if self.declared_delta_sign is DeltaSign.MINUS and self.declared_delta > 0:
                raise ValueError("MINUS sign cannot accompany a positive declared_delta")

    def _validate_date_state(self) -> None:
        has_date_text = self.event_date_text is not None and bool(self.event_date_text.strip())
        if self.date_precision is DatePrecision.FULL:
            if self.event_date is None or not has_date_text or self.date_span is None:
                raise ValueError("FULL date requires event_date, event_date_text and date_span")
            if self.event_day is not None or self.event_month is not None:
                raise ValueError("FULL date must not duplicate day/month fields")
        elif self.date_precision is DatePrecision.DAY_MONTH:
            if self.event_date is not None:
                raise ValueError("DAY_MONTH must not silently contain a full date")
            if self.event_day is None or self.event_month is None:
                raise ValueError("DAY_MONTH requires event_day and event_month")
            if not has_date_text or self.date_span is None:
                raise ValueError("DAY_MONTH requires event_date_text and date_span")
            try:
                date(2000, self.event_month, self.event_day)
            except ValueError as error:
                raise ValueError("DAY_MONTH contains a non-existent calendar date") from error
        elif self.date_precision is DatePrecision.MISSING:
            if any(
                value is not None
                for value in (
                    self.event_date,
                    self.event_day,
                    self.event_month,
                    self.event_date_text,
                    self.date_span,
                )
            ):
                raise ValueError("MISSING date must not carry date values or spans")
            if WarningCode.MISSING_EVENT_DATE not in _warning_codes(self.warnings):
                raise ValueError("MISSING date requires a MISSING_EVENT_DATE warning")
        else:
            if self.event_date is not None:
                raise ValueError("AMBIGUOUS date must not contain an accepted full date")
            if not has_date_text:
                raise ValueError("AMBIGUOUS date requires the ambiguous source text")
            if WarningCode.DATE_AMBIGUOUS not in _warning_codes(self.warnings):
                raise ValueError("AMBIGUOUS date requires a DATE_AMBIGUOUS warning")
            if not self.requires_review:
                raise ValueError("AMBIGUOUS date must require review")

    def _validate_rule_state(self) -> None:
        rule_parts = (
            self.matched_rule_id is not None,
            self.expected_delta is not None,
            self.rule_match_confidence is not None,
        )
        if len(set(rule_parts)) != 1:
            raise ValueError(
                "matched_rule_id, expected_delta and rule_match_confidence must appear together"
            )
        if self.matched_rule_id is not None:
            _require_nonblank(self.matched_rule_id, "matched_rule_id")

    def _validate_delta_state(self) -> None:
        deltas = (
            ("declared_delta", self.declared_delta),
            ("expected_delta", self.expected_delta),
            ("final_delta", self.final_delta),
        )
        for field_name, delta in deltas:
            if delta is not None:
                _validate_delta_direction(self.event_type, delta, field_name)
        if self.event_type is EventType.UNKNOWN and not self.requires_review:
            raise ValueError("UNKNOWN event type must require review")

        if (
            self.declared_delta is not None
            and self.expected_delta is not None
            and self.declared_delta != self.expected_delta
        ):
            if WarningCode.RULE_CONFLICT not in _warning_codes(self.warnings):
                raise ValueError("conflicting deltas require a RULE_CONFLICT warning")
            if not self.requires_review or self.review_status is not ReviewStatus.PENDING_REVIEW:
                raise ValueError("conflicting deltas must remain pending review")
            if self.final_delta is not None:
                raise ValueError("conflicting deltas cannot receive final_delta automatically")

    def _validate_review_state(self) -> None:
        accepted = {ReviewStatus.AUTO_ACCEPTED, ReviewStatus.APPROVED}
        if self.review_status in accepted:
            if self.final_delta is None or not self.review_record_id:
                raise ValueError("accepted events require final_delta and review_record_id")
            if self.requires_review:
                raise ValueError("accepted events cannot remain marked requires_review")
        elif self.review_status is ReviewStatus.REJECTED:
            if self.final_delta is not None or not self.review_record_id:
                raise ValueError("rejected events require review_record_id and no final_delta")
            if self.requires_review:
                raise ValueError("rejected events cannot remain marked requires_review")
        else:
            if self.final_delta is not None or self.review_record_id is not None:
                raise ValueError("unreviewed events cannot carry final review data")
            if self.review_status is ReviewStatus.PENDING_REVIEW and not self.requires_review:
                raise ValueError("PENDING_REVIEW must set requires_review")


class ValidationResult(DomainModel):
    """Deterministic validation outcome for one domain object."""

    is_valid: bool
    warnings: tuple[DomainWarning, ...] = ()
    errors: tuple[str, ...] = ()
    requires_review: bool = False

    @model_validator(mode="after")
    def validate_result_state(self) -> Self:
        if self.is_valid and self.errors:
            raise ValueError("a valid result cannot contain errors")
        if not self.is_valid and not self.errors:
            raise ValueError("an invalid result must explain at least one error")
        if any(warning.blocking for warning in self.warnings) and not self.requires_review:
            raise ValueError("blocking warnings must require review")
        if self.errors and not self.requires_review:
            raise ValueError("validation errors must require review")
        if any(not error.strip() for error in self.errors):
            raise ValueError("validation errors must not be blank")
        return self


class DuplicateMatch(DomainModel):
    """A non-destructive duplicate candidate relationship."""

    event_id: str
    duplicate_event_id: str
    similarity_score: ConfidenceDecimal
    reasons: tuple[str, ...] = Field(min_length=1)
    requires_review: bool = True

    @model_validator(mode="after")
    def validate_duplicate(self) -> Self:
        if self.event_id == self.duplicate_event_id:
            raise ValueError("a duplicate match must reference two different events")
        if not self.requires_review:
            raise ValueError("duplicate candidates must require review")
        if any(not reason.strip() for reason in self.reasons):
            raise ValueError("duplicate reasons must not be blank")
        return self


class ReviewRecord(DomainModel):
    """Append-only review decision record."""

    review_id: str
    event_id: str
    status: ReviewStatus
    action: ReviewAction | None = None
    reviewer_id: str | None = None
    reviewed_at: datetime | None = None
    reason: str | None = None
    final_delta: FiniteDecimal | None = None
    previous_review_id: str | None = None

    @model_validator(mode="after")
    def validate_review(self) -> Self:
        _require_nonblank(self.review_id, "review_id")
        _require_nonblank(self.event_id, "event_id")
        finalized = {
            ReviewStatus.AUTO_ACCEPTED,
            ReviewStatus.APPROVED,
            ReviewStatus.REJECTED,
        }
        if self.status in finalized:
            if self.action is None or self.reviewer_id is None or self.reviewed_at is None:
                raise ValueError("finalized review requires action, reviewer_id and reviewed_at")
            _require_nonblank(self.reviewer_id, "reviewer_id")
            if self.reason is None:
                raise ValueError("finalized review requires a reason")
            _require_nonblank(self.reason, "reason")
            _validate_timezone(self.reviewed_at, "reviewed_at")
        elif any(
            value is not None
            for value in (
                self.action,
                self.reviewer_id,
                self.reviewed_at,
                self.reason,
                self.final_delta,
            )
        ):
            raise ValueError("unfinished review cannot contain decision metadata")

        if self.status in {
            ReviewStatus.AUTO_ACCEPTED,
            ReviewStatus.APPROVED,
        } and (self.action is ReviewAction.REJECT_EVENT or self.final_delta is None):
            raise ValueError("accepted review requires a non-rejection action and final_delta")
        if self.status is ReviewStatus.REJECTED and (
            self.action is not ReviewAction.REJECT_EVENT or self.final_delta is not None
        ):
            raise ValueError("rejected review requires REJECT_EVENT and no final_delta")
        return self


class TimelineItem(DomainModel):
    """One immutable audit timeline entry."""

    item_id: str
    person_id: str
    event_id: str | None = None
    item_type: TimelineItemType
    occurred_at: datetime
    description: str
    actor_id: str

    @field_validator("item_id", "person_id", "description", "actor_id")
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        return _require_nonblank(value, "timeline text")

    @field_validator("occurred_at")
    @classmethod
    def validate_occurred_at(cls, value: datetime) -> datetime:
        return _validate_timezone(value, "occurred_at")


class ScoringPeriod(DomainModel):
    """Inclusive date range in which events may count."""

    period_id: str
    name: str
    starts_on: date
    ends_on: date
    academic_year_label: str

    @field_validator("period_id", "name", "academic_year_label")
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        return _require_nonblank(value, "scoring period text")

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.ends_on < self.starts_on:
            raise ValueError("scoring period end must not precede its start")
        return self


class DeclaredRowTotals(DomainModel):
    """Totals read from user-authored source columns."""

    base_score: FiniteDecimal | None = None
    positive_total: NonNegativeDecimal | None = None
    negative_total: NonNegativeDecimal | None = None
    final_total: FiniteDecimal | None = None


class CalculatedRowTotals(DomainModel):
    """Totals deterministically calculated from reviewed events."""

    base_score: FiniteDecimal | None = None
    positive_total: NonNegativeDecimal | None = None
    negative_total: NonNegativeDecimal | None = None
    final_total: FiniteDecimal | None = None

    @model_validator(mode="after")
    def validate_formula(self) -> Self:
        parts = (self.base_score, self.positive_total, self.negative_total, self.final_total)
        if all(value is not None for value in parts):
            assert self.base_score is not None
            assert self.positive_total is not None
            assert self.negative_total is not None
            assert self.final_total is not None
            expected = self.base_score + self.positive_total - self.negative_total
            if self.final_total != expected:
                raise ValueError("calculated final_total must equal base + positive - negative")
        return self


class PersonReconciliation(DomainModel):
    """Flat declared-versus-calculated totals and exact differences."""

    declared_positive_total: NonNegativeDecimal | None = None
    declared_negative_total: NonNegativeDecimal | None = None
    declared_final_total: FiniteDecimal | None = None
    calculated_positive_total: NonNegativeDecimal | None = None
    calculated_negative_total: NonNegativeDecimal | None = None
    calculated_final_total: FiniteDecimal | None = None
    positive_difference: FiniteDecimal | None = None
    negative_difference: FiniteDecimal | None = None
    final_difference: FiniteDecimal | None = None
    unresolved_event_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_differences(self) -> Self:
        pairs = (
            (
                "positive_difference",
                self.declared_positive_total,
                self.calculated_positive_total,
            ),
            (
                "negative_difference",
                self.declared_negative_total,
                self.calculated_negative_total,
            ),
            ("final_difference", self.declared_final_total, self.calculated_final_total),
        )
        for field_name, declared, calculated in pairs:
            supplied = getattr(self, field_name)
            if declared is None or calculated is None:
                if supplied is not None:
                    raise ValueError(f"{field_name} must be null when either total is missing")
                continue
            expected = calculated - declared
            if supplied is None:
                object.__setattr__(self, field_name, expected)
            elif supplied != expected:
                raise ValueError(f"{field_name} must equal calculated minus declared")
        return self

    @classmethod
    def from_totals(
        cls,
        *,
        declared: DeclaredRowTotals,
        calculated: CalculatedRowTotals,
        unresolved_event_count: int,
    ) -> PersonReconciliation:
        """Build a reconciliation without copying the base score into comparison fields."""
        return cls(
            declared_positive_total=declared.positive_total,
            declared_negative_total=declared.negative_total,
            declared_final_total=declared.final_total,
            calculated_positive_total=calculated.positive_total,
            calculated_negative_total=calculated.negative_total,
            calculated_final_total=calculated.final_total,
            unresolved_event_count=unresolved_event_count,
        )


class RuleDefinition(DomainModel):
    """Versioned deterministic scoring rule definition."""

    rule_id: str
    version: str
    name: str
    event_type: EventType
    expected_delta: FiniteDecimal
    priority: int = Field(ge=0)
    enabled: bool = True
    effective_from: date | None = None
    effective_to: date | None = None
    academic_score_min: FiniteDecimal | None = None
    academic_score_max: FiniteDecimal | None = None
    description_keywords: tuple[str, ...] = ()
    scoring_period_ids: tuple[str, ...] = ()
    requires_event_date: bool = False

    @field_validator("rule_id", "version", "name")
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        return _require_nonblank(value, "rule text")

    @model_validator(mode="after")
    def validate_rule(self) -> Self:
        _validate_delta_direction(self.event_type, self.expected_delta, "expected_delta")
        if self.event_type is EventType.UNKNOWN:
            raise ValueError("rule definitions cannot target UNKNOWN event type")
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise ValueError("rule effective_to must not precede effective_from")
        if (
            self.academic_score_min is not None
            and self.academic_score_max is not None
            and self.academic_score_max < self.academic_score_min
        ):
            raise ValueError("academic_score_max must not be below academic_score_min")
        if any(not keyword.strip() for keyword in self.description_keywords):
            raise ValueError("description keywords must not be blank")
        if len(set(self.description_keywords)) != len(self.description_keywords):
            raise ValueError("description keywords must be unique")
        if any(not period_id.strip() for period_id in self.scoring_period_ids):
            raise ValueError("scoring period IDs must not be blank")
        return self


class RuleMatch(DomainModel):
    """Traceable deterministic rule match result."""

    event_id: str
    status: RuleMatchStatus
    matched_rule_id: str | None = None
    candidate_rule_ids: tuple[str, ...] = ()
    expected_delta: FiniteDecimal | None = None
    confidence: ConfidenceDecimal | None = None
    trace: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_match(self) -> Self:
        _require_nonblank(self.event_id, "event_id")
        if any(not value.strip() for value in (*self.candidate_rule_ids, *self.trace)):
            raise ValueError("rule candidate IDs and trace entries must not be blank")
        if self.status is RuleMatchStatus.NO_MATCH:
            if any(
                value is not None
                for value in (self.matched_rule_id, self.expected_delta, self.confidence)
            ):
                raise ValueError("NO_MATCH cannot contain a selected rule, delta or confidence")
        elif self.status is RuleMatchStatus.ONE_MATCH:
            if (
                self.matched_rule_id is None
                or self.expected_delta is None
                or self.confidence is None
            ):
                raise ValueError("ONE_MATCH requires rule ID, expected_delta and confidence")
            if self.matched_rule_id not in self.candidate_rule_ids:
                raise ValueError("selected rule must appear in candidate_rule_ids")
        else:
            if len(self.candidate_rule_ids) < 2:
                raise ValueError("AMBIGUOUS_MATCH requires at least two candidates")
            if self.matched_rule_id is not None or self.expected_delta is not None:
                raise ValueError("AMBIGUOUS_MATCH cannot select a rule or expected delta")
        return self


class RuleConflict(DomainModel):
    """Explicit unresolved or reviewed disagreement between delta sources."""

    event_id: str
    rule_id: str
    declared_delta: FiniteDecimal
    expected_delta: FiniteDecimal
    warning_code: WarningCode = WarningCode.RULE_CONFLICT
    resolved: bool = False
    resolved_delta: FiniteDecimal | None = None
    review_record_id: str | None = None

    @model_validator(mode="after")
    def validate_conflict(self) -> Self:
        if self.declared_delta == self.expected_delta:
            raise ValueError("RuleConflict requires different declared and expected deltas")
        if self.warning_code is not WarningCode.RULE_CONFLICT:
            raise ValueError("RuleConflict must use the RULE_CONFLICT warning code")
        if self.resolved:
            if self.resolved_delta is None or not self.review_record_id:
                raise ValueError("resolved conflict requires resolved_delta and review_record_id")
        elif self.resolved_delta is not None or self.review_record_id is not None:
            raise ValueError("unresolved conflict cannot contain resolution data")
        return self


class DatePeriodValidation(DomainModel):
    """Explicit validation of an event date against a scoring period."""

    event_id: str
    scoring_period: ScoringPeriod
    date_precision: DatePrecision
    event_date: date | None = None
    event_day: int | None = Field(default=None, ge=1, le=31)
    event_month: int | None = Field(default=None, ge=1, le=12)
    candidate_dates: tuple[date, ...] = ()
    is_within_period: bool | None = None
    warnings: tuple[DomainWarning, ...] = ()

    @model_validator(mode="after")
    def validate_period_state(self) -> Self:
        codes = _warning_codes(self.warnings)
        if self.date_precision is DatePrecision.FULL:
            if (
                self.event_date is None
                or self.event_day is not None
                or self.event_month is not None
            ):
                raise ValueError("FULL period validation requires only event_date")
            expected = (
                self.scoring_period.starts_on
                <= self.event_date
                <= self.scoring_period.ends_on
            )
            if self.is_within_period is not expected:
                raise ValueError("is_within_period does not match the full event date")
            if not expected and WarningCode.DATE_OUTSIDE_PERIOD not in codes:
                raise ValueError("out-of-period date requires DATE_OUTSIDE_PERIOD warning")
        elif self.date_precision is DatePrecision.DAY_MONTH:
            if self.event_date is not None or self.event_day is None or self.event_month is None:
                raise ValueError("DAY_MONTH period validation requires day/month and no full date")
            try:
                date(2000, self.event_month, self.event_day)
            except ValueError as error:
                raise ValueError("DAY_MONTH contains a non-existent calendar date") from error
            for candidate in self.candidate_dates:
                if candidate.day != self.event_day or candidate.month != self.event_month:
                    raise ValueError("candidate dates must preserve the source day/month")
                if not (
                    self.scoring_period.starts_on <= candidate <= self.scoring_period.ends_on
                ):
                    raise ValueError("candidate dates must lie within the scoring period")
            expected = bool(self.candidate_dates)
            if self.is_within_period is not expected:
                raise ValueError("DAY_MONTH is_within_period must reflect candidate dates")
            if not expected and WarningCode.DATE_OUTSIDE_PERIOD not in codes:
                raise ValueError("DAY_MONTH without candidates requires DATE_OUTSIDE_PERIOD")
        else:
            if any(
                value is not None
                for value in (
                    self.event_date,
                    self.event_day,
                    self.event_month,
                    self.is_within_period,
                )
            ) or self.candidate_dates:
                raise ValueError("missing or ambiguous date cannot contain resolved period data")
            required_code = (
                WarningCode.MISSING_EVENT_DATE
                if self.date_precision is DatePrecision.MISSING
                else WarningCode.DATE_AMBIGUOUS
            )
            if required_code not in codes:
                raise ValueError("missing or ambiguous period validation requires its warning")
        return self


class PersonSummary(DomainModel):
    """Per-person audit summary tied to source provenance and a scoring period."""

    person_id: str
    full_name: str
    sheet_name: str
    excel_row: int = Field(ge=1)
    scoring_period_id: str
    reconciliation: PersonReconciliation
    event_ids: tuple[str, ...] = ()
    warnings: tuple[DomainWarning, ...] = ()
    requires_review: bool

    @field_validator("person_id", "full_name", "sheet_name", "scoring_period_id")
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        return _require_nonblank(value, "person summary text")

    @model_validator(mode="after")
    def validate_summary(self) -> Self:
        if len(set(self.event_ids)) != len(self.event_ids):
            raise ValueError("event_ids must be unique")
        expected_review = self.reconciliation.unresolved_event_count > 0 or any(
            warning.blocking for warning in self.warnings
        )
        if self.requires_review is not expected_review:
            raise ValueError("requires_review must reflect unresolved events and blocking warnings")
        return self
