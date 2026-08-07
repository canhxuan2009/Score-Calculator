"""Deterministic semantic parsing for one source-backed event candidate."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from point_audit.domain import (
    DatePrecision,
    DeltaSign,
    DomainWarning,
    EventCandidate,
    EventCategory,
    EventType,
    ParsedEvent,
    ParseSource,
    ReviewStatus,
    ScoringPeriod,
    TextSpan,
    WarningCode,
)

_PLUS_SIGNS = frozenset({"+", "＋", "﹢"})
_DELTA_RE = re.compile(
    r"(?P<sign>[+＋﹢\-−–—－﹣])\s*(?P<number>\d+(?:[.,]\d+)?)"
)
_DATE_RE = re.compile(
    r"(?<!\d)(?P<day>\d{1,2})/(?P<month>\d{1,2})"
    r"(?:/(?P<year>\d{4}))?(?!\d)"
)
_NUMBER_RE = re.compile(r"(?<![\d.,])\d{1,2}(?:[.,]\d+)?(?![\d.,])")
_ACADEMIC_UNIT_RE = re.compile(r"\s*(?:điểm|diem|đ|d)(?![A-Za-zÀ-ỹ])", re.IGNORECASE)
_NUMBER_BEFORE_SUBJECT_GAP_RE = re.compile(
    r"\s*(?:(?:điểm|diem|đ|d)\s*)?", re.IGNORECASE
)
_SUBJECT_BEFORE_NUMBER_GAP_RE = re.compile(r"\s*[:=]?\s*")

_SUBJECT_ALIASES: dict[str, tuple[str, ...]] = {
    "TOAN": ("toán", "toan"),
    "LY": ("vật lý", "vat ly", "lý", "lí", "ly", "li"),
    "HOA": ("hóa", "hoá", "hoa"),
    "SINH": ("sinh",),
    "SU": ("lịch sử", "lich su", "sử", "su"),
    "DIA": ("địa", "dia"),
    "TIN": ("tin học", "tin hoc", "tin"),
    "VAN": ("ngữ văn", "ngu van", "văn", "van"),
    "ANH": ("tiếng anh", "tieng anh", "anh"),
    "GDCD": ("gdcd",),
    "GDKTPL": ("gdktpl",),
}


@dataclass(frozen=True, slots=True)
class _SubjectMatch:
    canonical: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class _DeltaFields:
    value: Decimal | None
    sign: DeltaSign | None
    span: tuple[int, int] | None
    occupied_spans: tuple[tuple[int, int], ...]
    warnings: tuple[DomainWarning, ...]


@dataclass(frozen=True, slots=True)
class _DateFields:
    precision: DatePrecision
    text: str | None
    resolved_date: date | None
    day: int | None
    month: int | None
    span: tuple[int, int] | None
    year_inferred: bool
    occupied_spans: tuple[tuple[int, int], ...]
    warnings: tuple[DomainWarning, ...]


@dataclass(frozen=True, slots=True)
class _AcademicFields:
    score: Decimal | None
    score_span: tuple[int, int] | None
    subject: str | None
    subject_span: tuple[int, int] | None
    warnings: tuple[DomainWarning, ...]


def _warning(code: WarningCode, message: str, *, blocking: bool = False) -> DomainWarning:
    return DomainWarning(code=code, message_vi=message, blocking=blocking)


def _normalize_for_detection(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold()).replace("đ", "d")
    without_marks = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(without_marks.split())


def _normalize_description(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).split())


def _url_spans(raw_text: str) -> tuple[tuple[int, int], ...]:
    lowered = raw_text.casefold()
    spans: list[tuple[int, int]] = []
    cursor = 0
    while cursor < len(raw_text):
        starts = [
            position
            for marker in ("https://", "http://")
            if (position := lowered.find(marker, cursor)) >= 0
        ]
        if not starts:
            break
        start = min(starts)
        end = start
        while end < len(raw_text) and not raw_text[end].isspace():
            end += 1
        spans.append((start, end))
        cursor = end
    return tuple(spans)


def _overlaps(span: tuple[int, int], protected: tuple[tuple[int, int], ...]) -> bool:
    start, end = span
    return any(
        start < protected_end and end > protected_start
        for protected_start, protected_end in protected
    )


def _decimal(number_text: str) -> Decimal:
    return Decimal(number_text.replace(",", "."))


def _absolute_span(candidate: EventCandidate, span: tuple[int, int] | None) -> TextSpan | None:
    if span is None:
        return None
    return TextSpan(
        start=candidate.source_span.start + span[0],
        end=candidate.source_span.start + span[1],
    )


def _find_dates(raw_text: str) -> tuple[re.Match[str], ...]:
    urls = _url_spans(raw_text)
    return tuple(
        match
        for match in _DATE_RE.finditer(raw_text)
        if not _overlaps(match.span(), urls)
    )


def _invalid_date_fields(
    raw_text: str,
    match: re.Match[str],
    message: str,
) -> _DateFields:
    return _DateFields(
        precision=DatePrecision.AMBIGUOUS,
        text=match.group(0),
        resolved_date=None,
        day=None,
        month=None,
        span=match.span(),
        year_inferred=False,
        occupied_spans=(match.span(),),
        warnings=(
            _warning(WarningCode.INVALID_DATE, message, blocking=True),
            _warning(
                WarningCode.DATE_AMBIGUOUS,
                "Ngày sự kiện không thể được xác nhận.",
                blocking=True,
            ),
        ),
    )


def _outside_period_warning(event_date: date, scoring_period: ScoringPeriod) -> DomainWarning:
    return _warning(
        WarningCode.DATE_OUTSIDE_PERIOD,
        (
            f"Ngày {event_date.isoformat()} nằm ngoài kỳ "
            f"{scoring_period.starts_on.isoformat()}–{scoring_period.ends_on.isoformat()}."
        ),
    )


def _parse_day_month_with_period(
    raw_text: str,
    match: re.Match[str],
    *,
    day: int,
    month: int,
    scoring_period: ScoringPeriod,
) -> _DateFields:
    possible_dates: list[date] = []
    for year in range(scoring_period.starts_on.year, scoring_period.ends_on.year + 1):
        try:
            candidate_date = date(year, month, day)
        except ValueError:
            continue
        if scoring_period.starts_on <= candidate_date <= scoring_period.ends_on:
            possible_dates.append(candidate_date)

    if len(possible_dates) == 1:
        return _DateFields(
            precision=DatePrecision.FULL,
            text=match.group(0),
            resolved_date=possible_dates[0],
            day=None,
            month=None,
            span=match.span(),
            year_inferred=True,
            occupied_spans=(match.span(),),
            warnings=(),
        )

    if len(possible_dates) > 1:
        return _DateFields(
            precision=DatePrecision.AMBIGUOUS,
            text=match.group(0),
            resolved_date=None,
            day=None,
            month=None,
            span=match.span(),
            year_inferred=False,
            occupied_spans=(match.span(),),
            warnings=(
                _warning(
                    WarningCode.DATE_AMBIGUOUS,
                    "Ngày/tháng khớp nhiều năm trong ScoringPeriod.",
                    blocking=True,
                ),
            ),
        )

    if scoring_period.starts_on.year == scoring_period.ends_on.year:
        try:
            resolved = date(scoring_period.starts_on.year, month, day)
        except ValueError:
            return _invalid_date_fields(
                raw_text,
                match,
                f"Ngày '{match.group(0)}' không tồn tại trong năm của ScoringPeriod.",
            )
        return _DateFields(
            precision=DatePrecision.FULL,
            text=match.group(0),
            resolved_date=resolved,
            day=None,
            month=None,
            span=match.span(),
            year_inferred=True,
            occupied_spans=(match.span(),),
            warnings=(_outside_period_warning(resolved, scoring_period),),
        )

    return _DateFields(
        precision=DatePrecision.AMBIGUOUS,
        text=match.group(0),
        resolved_date=None,
        day=None,
        month=None,
        span=match.span(),
        year_inferred=False,
        occupied_spans=(match.span(),),
        warnings=(
            _warning(
                WarningCode.DATE_AMBIGUOUS,
                "Không thể suy ra duy nhất năm cho ngày/tháng từ ScoringPeriod.",
                blocking=True,
            ),
            _warning(
                WarningCode.DATE_OUTSIDE_PERIOD,
                "Ngày/tháng không tạo được ngày hợp lệ nằm trong ScoringPeriod.",
            ),
        ),
    )


def _parse_date(raw_text: str, scoring_period: ScoringPeriod | None) -> _DateFields:
    matches = _find_dates(raw_text)
    if not matches:
        return _DateFields(
            precision=DatePrecision.MISSING,
            text=None,
            resolved_date=None,
            day=None,
            month=None,
            span=None,
            year_inferred=False,
            occupied_spans=(),
            warnings=(
                _warning(
                    WarningCode.MISSING_EVENT_DATE,
                    "Sự kiện không khai báo ngày.",
                ),
            ),
        )
    if len(matches) > 1:
        combined_span = (matches[0].start(), matches[-1].end())
        return _DateFields(
            precision=DatePrecision.AMBIGUOUS,
            text=raw_text[combined_span[0] : combined_span[1]],
            resolved_date=None,
            day=None,
            month=None,
            span=combined_span,
            year_inferred=False,
            occupied_spans=tuple(match.span() for match in matches),
            warnings=(
                _warning(
                    WarningCode.DATE_AMBIGUOUS,
                    "Sự kiện chứa nhiều ngày nên parser không tự chọn.",
                    blocking=True,
                ),
            ),
        )

    match = matches[0]
    day = int(match.group("day"))
    month = int(match.group("month"))
    year_text = match.group("year")
    if year_text is not None:
        try:
            resolved = date(int(year_text), month, day)
        except ValueError:
            return _invalid_date_fields(
                raw_text, match, f"Ngày '{match.group(0)}' không tồn tại."
            )
        warnings: tuple[DomainWarning, ...] = ()
        if scoring_period is not None and not (
            scoring_period.starts_on <= resolved <= scoring_period.ends_on
        ):
            warnings = (_outside_period_warning(resolved, scoring_period),)
        return _DateFields(
            precision=DatePrecision.FULL,
            text=match.group(0),
            resolved_date=resolved,
            day=None,
            month=None,
            span=match.span(),
            year_inferred=False,
            occupied_spans=(match.span(),),
            warnings=warnings,
        )

    try:
        date(2000, month, day)
    except ValueError:
        return _invalid_date_fields(
            raw_text, match, f"Ngày/tháng '{match.group(0)}' không tồn tại."
        )

    if scoring_period is not None:
        return _parse_day_month_with_period(
            raw_text,
            match,
            day=day,
            month=month,
            scoring_period=scoring_period,
        )
    return _DateFields(
        precision=DatePrecision.DAY_MONTH,
        text=match.group(0),
        resolved_date=None,
        day=day,
        month=month,
        span=match.span(),
        year_inferred=False,
        occupied_spans=(match.span(),),
        warnings=(),
    )


def _delta_token_end(raw_text: str, number_end: int) -> int:
    unit_match = _ACADEMIC_UNIT_RE.match(raw_text[number_end:])
    if unit_match is None:
        return number_end
    return number_end + unit_match.end()


def _parse_declared_delta(
    raw_text: str,
    *,
    date_spans: tuple[tuple[int, int], ...],
) -> _DeltaFields:
    protected = (*_url_spans(raw_text), *date_spans)
    matches: list[tuple[re.Match[str], tuple[int, int]]] = []
    for match in _DELTA_RE.finditer(raw_text):
        token_span = (match.start(), _delta_token_end(raw_text, match.end("number")))
        if not _overlaps(token_span, protected):
            matches.append((match, token_span))

    occupied = tuple(token_span for _, token_span in matches)
    if not matches:
        return _DeltaFields(
            value=None,
            sign=None,
            span=None,
            occupied_spans=(),
            warnings=(
                _warning(
                    WarningCode.MISSING_DECLARED_DELTA,
                    "Sự kiện không có điểm cộng/trừ được viết trực tiếp.",
                ),
            ),
        )
    if len(matches) > 1:
        return _DeltaFields(
            value=None,
            sign=None,
            span=None,
            occupied_spans=occupied,
            warnings=(
                _warning(
                    WarningCode.SEGMENTATION_AMBIGUOUS,
                    "Sự kiện chứa nhiều điểm cộng/trừ; parser không tự chọn một giá trị.",
                    blocking=True,
                ),
            ),
        )

    match, token_span = matches[0]
    sign = DeltaSign.PLUS if match.group("sign") in _PLUS_SIGNS else DeltaSign.MINUS
    magnitude = _decimal(match.group("number"))
    value = magnitude if sign is DeltaSign.PLUS else -magnitude
    return _DeltaFields(
        value=value,
        sign=sign,
        span=token_span,
        occupied_spans=occupied,
        warnings=(),
    )


def _find_subjects(raw_text: str) -> tuple[_SubjectMatch, ...]:
    matches: list[_SubjectMatch] = []
    for canonical, aliases in _SUBJECT_ALIASES.items():
        for alias in sorted(aliases, key=len, reverse=True):
            for alias_match in re.finditer(re.escape(alias), raw_text, re.IGNORECASE):
                start, end = alias_match.span()
                if start > 0 and raw_text[start - 1].isalpha():
                    continue
                if end < len(raw_text) and raw_text[end].isalpha():
                    continue
                matches.append(_SubjectMatch(canonical=canonical, start=start, end=end))
    matches.sort(key=lambda item: (item.start, -(item.end - item.start)))
    accepted: list[_SubjectMatch] = []
    for match in matches:
        if not any(
            match.start < current.end and match.end > current.start for current in accepted
        ):
            accepted.append(match)
    return tuple(accepted)


def _associated_subject(
    raw_text: str,
    number_span: tuple[int, int],
    subjects: tuple[_SubjectMatch, ...],
) -> _SubjectMatch | None:
    candidates: list[tuple[int, _SubjectMatch]] = []
    number_start, number_end = number_span
    for subject in subjects:
        if number_end <= subject.start:
            gap = raw_text[number_end : subject.start]
            if _NUMBER_BEFORE_SUBJECT_GAP_RE.fullmatch(gap) is not None:
                candidates.append((subject.start - number_end, subject))
        elif subject.end <= number_start:
            gap = raw_text[subject.end : number_start]
            if _SUBJECT_BEFORE_NUMBER_GAP_RE.fullmatch(gap) is not None:
                candidates.append((number_start - subject.end, subject))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1].start))
    return candidates[0][1]


def _has_academic_unit(raw_text: str, number_end: int) -> bool:
    return _ACADEMIC_UNIT_RE.match(raw_text[number_end:]) is not None


def _parse_academic_score(
    raw_text: str,
    *,
    protected_spans: tuple[tuple[int, int], ...],
) -> _AcademicFields:
    subjects = _find_subjects(raw_text)
    candidates: list[tuple[Decimal, tuple[int, int], _SubjectMatch | None]] = []
    for match in _NUMBER_RE.finditer(raw_text):
        span = match.span()
        if _overlaps(span, protected_spans):
            continue
        value = _decimal(match.group(0))
        if value < 0 or value > 10:
            continue
        subject = _associated_subject(raw_text, span, subjects)
        if subject is not None or _has_academic_unit(raw_text, match.end()):
            candidates.append((value, span, subject))

    if len(candidates) > 1:
        unique_subject = subjects[0] if len(subjects) == 1 else None
        return _AcademicFields(
            score=None,
            score_span=None,
            subject=unique_subject.canonical if unique_subject is not None else None,
            subject_span=(unique_subject.start, unique_subject.end)
            if unique_subject is not None
            else None,
            warnings=(
                _warning(
                    WarningCode.SEGMENTATION_AMBIGUOUS,
                    "Sự kiện chứa nhiều điểm môn học; parser không tự chọn.",
                    blocking=True,
                ),
            ),
        )
    if len(candidates) == 1:
        score, score_span, associated = candidates[0]
        subject = associated
        if subject is None and len(subjects) == 1:
            subject = subjects[0]
        return _AcademicFields(
            score=score,
            score_span=score_span,
            subject=subject.canonical if subject is not None else None,
            subject_span=(subject.start, subject.end) if subject is not None else None,
            warnings=(),
        )

    unique_subject = subjects[0] if len(subjects) == 1 else None
    return _AcademicFields(
        score=None,
        score_span=None,
        subject=unique_subject.canonical if unique_subject is not None else None,
        subject_span=(unique_subject.start, unique_subject.end)
        if unique_subject is not None
        else None,
        warnings=(),
    )


def _contains_any(normalized_text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in normalized_text for phrase in phrases)


def _classify_category(
    raw_text: str,
    *,
    academic_score: Decimal | None,
    subject: str | None,
) -> EventCategory:
    normalized = _normalize_for_detection(raw_text)
    if academic_score is not None:
        return EventCategory.ACADEMIC_SCORE
    if _contains_any(
        normalized,
        ("dat giai", "giai nhat", "giai nhi", "giai ba", "giai 1", "giai 2", "giai 3"),
    ):
        return EventCategory.COMPETITION_AWARD
    if _contains_any(normalized, ("di muon", "di hoc muon", "vang", "nghi hoc", "tre hoc")):
        return EventCategory.ATTENDANCE
    if _contains_any(
        normalized,
        ("lop truong", "lop pho", "to truong", "to pho", "can su", "co do", "vai tro"),
    ):
        return EventCategory.ROLE
    if _contains_any(
        normalized,
        ("dien van nghe", "van nghe", "bieu dien", "mit tinh", "mua van nghe", "ca hat"),
    ):
        return EventCategory.PERFORMANCE
    if _contains_any(
        normalized,
        ("da bong", "bong da", "keo co", "the thao", "cau long", "bong chuyen"),
    ):
        return EventCategory.SPORTS
    if "tham gia" in normalized and _contains_any(
        normalized, ("cuoc thi", "hoi thi", "thi ", "ky thi")
    ):
        return EventCategory.COMPETITION_PARTICIPATION
    if _contains_any(
        normalized,
        ("truc nhat", "ve sinh lop", "lao dong lop", "nhiem vu lop"),
    ):
        return EventCategory.CLASS_DUTY
    if "dat" in normalized and (
        subject is not None or _contains_any(normalized, ("hdtn", "hoc tap", "mon "))
    ):
        return EventCategory.SUBJECT_ACHIEVEMENT
    if _contains_any(
        normalized,
        ("vi pham", "quen", "noi chuyen", "mat trat tu", "khong lam", "gay go"),
    ):
        return EventCategory.NEGATIVE_BEHAVIOR
    if _contains_any(
        normalized,
        ("giup lop", "giup do", "tich cuc", "viec tot", "nhat duoc", "tuyen duong"),
    ):
        return EventCategory.POSITIVE_BEHAVIOR
    return EventCategory.OTHER


def _parse_source(candidate: EventCandidate) -> ParseSource:
    if candidate.parse_source in {ParseSource.AI, ParseSource.HYBRID}:
        return ParseSource.HYBRID
    return ParseSource.DETERMINISTIC


def parse_event_candidate(
    candidate: EventCandidate,
    *,
    scoring_period: ScoringPeriod | None = None,
) -> ParsedEvent:
    """Parse one candidate without applying rules or inventing expected/final points."""
    raw_text = candidate.raw_text
    parsed_date = _parse_date(raw_text, scoring_period)
    parsed_delta = _parse_declared_delta(
        raw_text,
        date_spans=parsed_date.occupied_spans,
    )
    parsed_academic = _parse_academic_score(
        raw_text,
        protected_spans=(
            *parsed_date.occupied_spans,
            *parsed_delta.occupied_spans,
            *_url_spans(raw_text),
        ),
    )
    category = _classify_category(
        raw_text,
        academic_score=parsed_academic.score,
        subject=parsed_academic.subject,
    )

    warnings = (
        *candidate.warnings,
        *parsed_date.warnings,
        *parsed_delta.warnings,
        *parsed_academic.warnings,
    )
    if parsed_delta.sign is DeltaSign.PLUS:
        event_type = EventType.BONUS
    elif parsed_delta.sign is DeltaSign.MINUS:
        event_type = EventType.PENALTY
    else:
        event_type = EventType.UNKNOWN

    requires_review = bool(warnings) or event_type is EventType.UNKNOWN
    ambiguous_codes = {
        WarningCode.SEGMENTATION_AMBIGUOUS,
        WarningCode.DATE_AMBIGUOUS,
        WarningCode.INVALID_DATE,
    }
    final_confidence = (
        Decimal("0.5")
        if any(warning.code in ambiguous_codes for warning in warnings)
        else Decimal("1")
    )

    return ParsedEvent(
        event_id=candidate.event_id,
        person_id=candidate.person_id,
        source_cell=candidate.source_cell,
        source_span=candidate.source_span,
        candidate_index=candidate.candidate_index,
        raw_text=candidate.raw_text,
        parse_source=_parse_source(candidate),
        reported_confidence=candidate.reported_confidence,
        warnings=warnings,
        event_type=event_type,
        event_category=category,
        description=_normalize_description(raw_text),
        evidence_text=raw_text,
        subject=parsed_academic.subject,
        subject_span=_absolute_span(candidate, parsed_academic.subject_span),
        academic_score=parsed_academic.score,
        academic_score_span=_absolute_span(candidate, parsed_academic.score_span),
        declared_delta=parsed_delta.value,
        declared_delta_sign=parsed_delta.sign,
        declared_delta_span=_absolute_span(candidate, parsed_delta.span),
        expected_delta=None,
        final_delta=None,
        date_span=_absolute_span(candidate, parsed_date.span),
        event_date_text=parsed_date.text,
        event_date=parsed_date.resolved_date,
        event_day=parsed_date.day,
        event_month=parsed_date.month,
        date_year_inferred=parsed_date.year_inferred,
        date_precision=parsed_date.precision,
        matched_rule_id=None,
        rule_match_confidence=None,
        final_confidence=final_confidence,
        requires_review=requires_review,
        review_status=(
            ReviewStatus.PENDING_REVIEW if requires_review else ReviewStatus.UNREVIEWED
        ),
        review_record_id=None,
    )
