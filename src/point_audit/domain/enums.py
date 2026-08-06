"""Enumerations used by the Point Audit domain contract."""

from enum import StrEnum


class SourceColumn(StrEnum):
    """Canonical source columns found in the workbook."""

    SEQUENCE = "SEQUENCE"
    FULL_NAME = "FULL_NAME"
    BIRTH_DATE = "BIRTH_DATE"
    GROUP = "GROUP"
    BASE_SCORE = "BASE_SCORE"
    POSITIVE_TOTAL = "POSITIVE_TOTAL"
    NEGATIVE_TOTAL = "NEGATIVE_TOTAL"
    FINAL_TOTAL = "FINAL_TOTAL"
    CONDUCT = "CONDUCT"
    EVIDENCE = "EVIDENCE"
    UNKNOWN = "UNKNOWN"


class EventType(StrEnum):
    """Scoring direction represented by an event."""

    BONUS = "BONUS"
    PENALTY = "PENALTY"
    INFORMATIONAL = "INFORMATIONAL"
    UNKNOWN = "UNKNOWN"


class DeltaSign(StrEnum):
    """Explicit sign written for a declared delta."""

    PLUS = "PLUS"
    MINUS = "MINUS"


class DatePrecision(StrEnum):
    """How precisely an event date is known."""

    FULL = "FULL"
    DAY_MONTH = "DAY_MONTH"
    MISSING = "MISSING"
    AMBIGUOUS = "AMBIGUOUS"


class ParseSource(StrEnum):
    """Origin of parsed semantic information."""

    DETERMINISTIC = "DETERMINISTIC"
    AI = "AI"
    MANUAL = "MANUAL"
    HYBRID = "HYBRID"


class WarningCode(StrEnum):
    """Stable machine-readable warning codes."""

    HEADER_NOT_FOUND = "HEADER_NOT_FOUND"
    HEADER_AMBIGUOUS = "HEADER_AMBIGUOUS"
    MISSING_REQUIRED_COLUMN = "MISSING_REQUIRED_COLUMN"
    UNKNOWN_ROW = "UNKNOWN_ROW"
    INVALID_NUMBER = "INVALID_NUMBER"
    INVALID_DATE = "INVALID_DATE"
    DATE_AMBIGUOUS = "DATE_AMBIGUOUS"
    DATE_OUTSIDE_PERIOD = "DATE_OUTSIDE_PERIOD"
    MISSING_EVENT_DATE = "MISSING_EVENT_DATE"
    MISSING_DECLARED_DELTA = "MISSING_DECLARED_DELTA"
    SEGMENTATION_AMBIGUOUS = "SEGMENTATION_AMBIGUOUS"
    AI_OUTPUT_INVALID = "AI_OUTPUT_INVALID"
    NO_RULE_MATCH = "NO_RULE_MATCH"
    AMBIGUOUS_RULE_MATCH = "AMBIGUOUS_RULE_MATCH"
    RULE_CONFLICT = "RULE_CONFLICT"
    DUPLICATE_CANDIDATE = "DUPLICATE_CANDIDATE"
    SOURCE_TOTAL_MISMATCH = "SOURCE_TOTAL_MISMATCH"
    UNRESOLVED_EVENT = "UNRESOLVED_EVENT"
    INVALID_EVENT_STATE = "INVALID_EVENT_STATE"
    MISSING_REVIEW_INFORMATION = "MISSING_REVIEW_INFORMATION"


class ReviewStatus(StrEnum):
    """Human or deterministic review state for an event."""

    UNREVIEWED = "UNREVIEWED"
    PENDING_REVIEW = "PENDING_REVIEW"
    AUTO_ACCEPTED = "AUTO_ACCEPTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ReviewAction(StrEnum):
    """Auditable action applied by a reviewer or approved policy."""

    USE_DECLARED = "USE_DECLARED"
    USE_EXPECTED = "USE_EXPECTED"
    SET_CUSTOM = "SET_CUSTOM"
    REJECT_EVENT = "REJECT_EVENT"
    EDIT_PARSED_FIELDS = "EDIT_PARSED_FIELDS"


class RuleMatchStatus(StrEnum):
    """Deterministic outcome of rule matching."""

    NO_MATCH = "NO_MATCH"
    ONE_MATCH = "ONE_MATCH"
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"


class TimelineItemType(StrEnum):
    """Kinds of auditable event timeline entries."""

    DISCOVERED = "DISCOVERED"
    PARSED = "PARSED"
    VALIDATED = "VALIDATED"
    RULE_MATCHED = "RULE_MATCHED"
    DUPLICATE_FLAGGED = "DUPLICATE_FLAGGED"
    REVIEWED = "REVIEWED"

