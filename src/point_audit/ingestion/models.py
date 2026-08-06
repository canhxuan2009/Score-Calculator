"""Typed, immutable results produced by workbook ingestion."""

from __future__ import annotations

import re
from datetime import date
from typing import Self

from pydantic import Field, field_validator, model_validator

from point_audit.domain import (
    DomainWarning,
    FiniteDecimal,
    NonNegativeDecimal,
    RawWorkbookRow,
    ScoringPeriod,
    SourceColumn,
)
from point_audit.domain.types import DomainModel

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _nonblank(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


class DetectedColumn(DomainModel):
    """Mapping from a physical header cell to a canonical source column."""

    source_column: SourceColumn
    excel_column: int = Field(ge=1)
    source_column_name: str

    @field_validator("source_column_name")
    @classmethod
    def validate_source_column_name(cls, value: str) -> str:
        return _nonblank(value, "source_column_name")


class IngestedStudentRow(DomainModel):
    """One student-like workbook row before event parsing."""

    source_file_sha256: str
    sheet_name: str
    excel_row: int = Field(ge=1)
    sequence_raw: str | None = None
    sequence_number: int | None = Field(default=None, ge=0)
    full_name_raw: str | None = None
    birth_date_raw: str | None = None
    birth_date: date | None = None
    group_raw: str | None = None
    base_score_raw: str | None = None
    base_score: FiniteDecimal | None = None
    declared_positive_raw: str | None = None
    declared_positive_total: NonNegativeDecimal | None = None
    declared_negative_raw: str | None = None
    declared_negative_total: NonNegativeDecimal | None = None
    declared_final_raw: str | None = None
    declared_final_total: FiniteDecimal | None = None
    conduct_raw: str | None = None
    evidence_raw: str = ""
    raw_row: RawWorkbookRow
    warnings: tuple[DomainWarning, ...] = ()

    @field_validator("source_file_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        normalized = value.lower()
        if _SHA256_PATTERN.fullmatch(normalized) is None:
            raise ValueError("source_file_sha256 must be a hexadecimal SHA-256")
        return normalized

    @field_validator("sheet_name")
    @classmethod
    def validate_sheet_name(cls, value: str) -> str:
        return _nonblank(value, "sheet_name")

    @model_validator(mode="after")
    def validate_provenance(self) -> Self:
        if self.sequence_number is None and not (self.full_name_raw or "").strip():
            raise ValueError("a student row requires numeric TT and/or a nonblank full name")
        if self.raw_row.source_file_sha256 != self.source_file_sha256:
            raise ValueError("raw_row must reference the same source file")
        if self.raw_row.sheet_name != self.sheet_name or self.raw_row.excel_row != self.excel_row:
            raise ValueError("raw_row must reference the same sheet and Excel row")
        return self


class WorkbookIngestionResult(DomainModel):
    """Complete read-only ingestion result for the single supported sheet."""

    source_file_name: str
    source_file_sha256: str
    sheet_name: str
    header_row: int = Field(ge=1)
    columns: tuple[DetectedColumn, ...] = Field(min_length=5)
    scoring_period: ScoringPeriod | None = None
    students: tuple[IngestedStudentRow, ...]
    stopped_at_row: int | None = Field(default=None, ge=1)
    formulas_found: bool = False
    cached_formula_values_found: bool = False
    warnings: tuple[DomainWarning, ...] = ()

    @field_validator("source_file_name", "sheet_name")
    @classmethod
    def validate_names(cls, value: str) -> str:
        return _nonblank(value, "source name")

    @field_validator("source_file_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        normalized = value.lower()
        if _SHA256_PATTERN.fullmatch(normalized) is None:
            raise ValueError("source_file_sha256 must be a hexadecimal SHA-256")
        return normalized

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        canonical_columns = [column.source_column for column in self.columns]
        if len(canonical_columns) != len(set(canonical_columns)):
            raise ValueError("columns cannot contain duplicate canonical source columns")
        if self.cached_formula_values_found and not self.formulas_found:
            raise ValueError("cached formula values require at least one formula")
        for student in self.students:
            if student.source_file_sha256 != self.source_file_sha256:
                raise ValueError("all students must reference the result source file")
            if student.sheet_name != self.sheet_name or student.excel_row <= self.header_row:
                raise ValueError("student provenance must follow the detected header")
        return self
