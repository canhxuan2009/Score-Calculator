"""Reusable constrained types and source identity helpers."""

from __future__ import annotations

import hashlib
from decimal import Decimal
from typing import Annotated, Any, Self

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def _reject_float(value: Any) -> Any:
    if isinstance(value, float):
        raise ValueError("float values are forbidden; use Decimal or a decimal string")
    if isinstance(value, bool):
        raise ValueError("boolean values are not valid decimals")
    return value


def _ensure_finite(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise ValueError("decimal values must be finite")
    return value


FiniteDecimal = Annotated[
    Decimal,
    BeforeValidator(_reject_float),
    AfterValidator(_ensure_finite),
]
NonNegativeDecimal = Annotated[FiniteDecimal, Field(ge=Decimal("0"))]
ConfidenceDecimal = Annotated[
    FiniteDecimal,
    Field(ge=Decimal("0"), le=Decimal("1")),
]


class DomainModel(BaseModel):
    """Strict immutable base for all persisted domain values."""

    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)


class TextSpan(DomainModel):
    """Half-open character span relative to a source cell's raw text."""

    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_order(self) -> Self:
        if self.end <= self.start:
            raise ValueError("span end must be greater than span start")
        return self


def build_event_id(
    *,
    source_file_sha256: str,
    sheet_name: str,
    excel_row: int,
    excel_column: int,
    source_column_name: str,
    source_span: TextSpan,
    candidate_index: int,
    raw_text: str,
) -> str:
    """Create a stable event ID from immutable source identity and position."""
    identity = "\x1f".join(
        (
            source_file_sha256.lower(),
            sheet_name,
            str(excel_row),
            str(excel_column),
            source_column_name,
            str(source_span.start),
            str(source_span.end),
            str(candidate_index),
            raw_text,
        )
    )
    return f"evt_{hashlib.sha256(identity.encode('utf-8')).hexdigest()}"

