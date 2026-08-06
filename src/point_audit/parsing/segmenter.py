"""Deterministic, lossless segmentation of free-form evidence text.

The segmenter deliberately does not interpret business rules or calculate points.  It only
identifies conservative event boundaries and preserves enough source information for later
semantic parsing and audit.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum, auto

from point_audit.domain import (
    DomainWarning,
    EventCandidate,
    ParseSource,
    RawCell,
    TextSpan,
    WarningCode,
)

_PLUS_SIGNS = frozenset({"+", "＋", "﹢"})
_MINUS_SIGNS = frozenset({"-", "−", "–", "—", "－", "﹣"})
_DELTA_SIGNS = _PLUS_SIGNS | _MINUS_SIGNS
_OPENING_BRACKETS = frozenset({"(", "[", "{", "（"})
_CLOSING_BRACKETS = frozenset({")", "]", "}", "）"})
_STRONG_DELIMITERS = frozenset({";", "\r", "\n"})

# These expressions each answer one narrow lexical question.  Boundary decisions are made by
# normal Python functions below instead of by one monolithic regular expression.
_DELTA_RE = re.compile(r"[+＋﹢\-−–—－﹣]\s*\d+(?:[.,]\d+)?")
_DATE_AT_START_RE = re.compile(
    r"(?:0?[1-9]|[12]\d|3[01])\s*[/.-]\s*(?:0?[1-9]|1[0-2])"
    r"(?:\s*[/.-]\s*\d{2,4})?"
)
_ACADEMIC_START_RE = re.compile(
    r"\d{1,2}(?:[.,]\d+)?\s*(?:d(?:iem)?)?\s*"
    r"(?:toan|li|ly|hoa|sinh|su|dia|tin|van|anh|vat\s*ly|ngu\s*van|gdcd|gdktpl)\b",
    re.IGNORECASE,
)

_ACTIVITY_PREFIXES = (
    "tham gia",
    "truc nhat",
    "giup lop",
    "giup",
    "di hoc muon",
    "di muon",
    "vi pham",
    "quen khan",
    "quen",
    "da bong",
    "keo co",
    "dien van nghe",
    "van nghe",
    "mit tinh",
    "lao dong",
    "hdtn",
)


class _EventStartKind(Enum):
    NONE = auto()
    EXPLICIT_DELTA = auto()
    ACADEMIC_SCORE = auto()
    ACHIEVEMENT = auto()
    ACTIVITY = auto()
    DATE_WITH_CONTENT = auto()


class _CommaDecision(Enum):
    KEEP = auto()
    SPLIT = auto()
    AMBIGUOUS_KEEP = auto()


@dataclass(frozen=True, slots=True)
class EventSegment:
    """One exact source substring and the exact delimiter that follows it."""

    raw_text: str
    source_span: TextSpan
    delimiter_after: str = ""
    warnings: tuple[DomainWarning, ...] = ()


@dataclass(frozen=True, slots=True)
class SegmentationResult:
    """Lossless result of one deterministic segmentation pass."""

    raw_text: str
    leading_text: str
    segments: tuple[EventSegment, ...]
    warnings: tuple[DomainWarning, ...] = ()

    def __post_init__(self) -> None:
        reconstructed = self.leading_text + "".join(
            segment.raw_text + segment.delimiter_after for segment in self.segments
        )
        if reconstructed != self.raw_text:
            raise ValueError("segmentation result must reconstruct the exact source text")
        for segment in self.segments:
            start = segment.source_span.start
            end = segment.source_span.end
            if self.raw_text[start:end] != segment.raw_text:
                raise ValueError("segment span must reference its exact source substring")

    @property
    def is_ambiguous(self) -> bool:
        """Whether at least one boundary has more than one reasonable interpretation."""
        return any(warning.code is WarningCode.SEGMENTATION_AMBIGUOUS for warning in self.warnings)


@dataclass(slots=True)
class _SegmentDraft:
    start: int
    end: int
    delimiter_after: str


@dataclass(frozen=True, slots=True)
class _Issue:
    position: int
    warning: DomainWarning


def _normalize_for_detection(value: str) -> str:
    """Normalize a short preview for matching without changing source text or offsets."""
    decomposed = unicodedata.normalize("NFD", value.casefold()).replace("đ", "d")
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def is_decimal_comma(raw_text: str, comma_index: int) -> bool:
    """Return true only for a comma immediately surrounded by decimal digits."""
    if comma_index < 0 or comma_index >= len(raw_text) or raw_text[comma_index] != ",":
        return False
    return (
        comma_index > 0
        and comma_index + 1 < len(raw_text)
        and raw_text[comma_index - 1].isdigit()
        and raw_text[comma_index + 1].isdigit()
    )


def _url_spans(raw_text: str) -> tuple[tuple[int, int], ...]:
    """Find URL-like tokens so their internal punctuation cannot become a boundary."""
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
        token_end = start
        while token_end < len(raw_text) and not raw_text[token_end].isspace():
            token_end += 1
        # A comma/semicolon immediately before whitespace is much more likely to delimit the
        # evidence than to be part of the URL.  Internal URL punctuation remains protected.
        protected_end = token_end
        while protected_end > start and raw_text[protected_end - 1] in {",", ";"}:
            protected_end -= 1
        spans.append((start, protected_end))
        cursor = token_end
    return tuple(spans)


def _url_end_at(position: int, spans: tuple[tuple[int, int], ...]) -> int | None:
    for start, end in spans:
        if start == position:
            return end
    return None


def _position_in_url(position: int, spans: tuple[tuple[int, int], ...]) -> bool:
    return any(start <= position < end for start, end in spans)


def _contains_delta(value: str) -> bool:
    spans = _url_spans(value)
    return any(not _position_in_url(match.start(), spans) for match in _DELTA_RE.finditer(value))


def _starts_with_delta(raw_text: str, position: int) -> bool:
    if position >= len(raw_text) or raw_text[position] not in _DELTA_SIGNS:
        return False
    cursor = position + 1
    while cursor < len(raw_text) and raw_text[cursor].isspace():
        cursor += 1
    return cursor < len(raw_text) and raw_text[cursor].isdigit()


def _starts_with_academic_score(raw_text: str, position: int) -> bool:
    preview = _normalize_for_detection(raw_text[position : position + 80])
    return _ACADEMIC_START_RE.match(preview) is not None


def _starts_with_word(normalized_preview: str, word: str) -> bool:
    if not normalized_preview.startswith(word):
        return False
    if len(normalized_preview) == len(word):
        return True
    following = normalized_preview[len(word)]
    return not following.isalnum() and following != "_"


def _event_start_kind(raw_text: str, position: int) -> _EventStartKind:
    if position >= len(raw_text):
        return _EventStartKind.NONE
    if _starts_with_delta(raw_text, position):
        return _EventStartKind.EXPLICIT_DELTA
    if _starts_with_academic_score(raw_text, position):
        return _EventStartKind.ACADEMIC_SCORE

    preview = _normalize_for_detection(raw_text[position : position + 100]).lstrip()
    if _starts_with_word(preview, "dat"):
        return _EventStartKind.ACHIEVEMENT
    if any(_starts_with_word(preview, prefix) for prefix in _ACTIVITY_PREFIXES):
        return _EventStartKind.ACTIVITY

    date_match = _DATE_AT_START_RE.match(raw_text[position:])
    if date_match is not None:
        remainder = raw_text[position + date_match.end() : position + date_match.end() + 50]
        if any(character.isalpha() for character in remainder):
            return _EventStartKind.DATE_WITH_CONTENT
    return _EventStartKind.NONE


def starts_new_event(raw_text: str, position: int) -> bool:
    """Expose the lexical event-start signal for focused unit tests and later tuning."""
    return _event_start_kind(raw_text, position) is not _EventStartKind.NONE


def _skip_whitespace(raw_text: str, position: int) -> int:
    while position < len(raw_text) and raw_text[position].isspace():
        position += 1
    return position


def _trim_whitespace_left(raw_text: str, position: int, lower_bound: int) -> int:
    while position > lower_bound and raw_text[position - 1].isspace():
        position -= 1
    return position


def _consume_punctuation_run(raw_text: str, position: int) -> tuple[int, bool]:
    """Consume adjacent separators/spaces and report whether a strong separator occurred."""
    cursor = position
    strong_found = False
    while cursor < len(raw_text):
        character = raw_text[cursor]
        if character in _STRONG_DELIMITERS:
            strong_found = True
            cursor += 1
        elif character == "," or character.isspace():
            cursor += 1
        else:
            break
    return cursor, strong_found


def _comma_decision(raw_text: str, left_text: str, right_start: int) -> _CommaDecision:
    kind = _event_start_kind(raw_text, right_start)
    if kind in {_EventStartKind.EXPLICIT_DELTA, _EventStartKind.ACADEMIC_SCORE}:
        return _CommaDecision.SPLIT
    if kind in {
        _EventStartKind.ACHIEVEMENT,
        _EventStartKind.ACTIVITY,
        _EventStartKind.DATE_WITH_CONTENT,
    }:
        if _contains_delta(left_text):
            return _CommaDecision.SPLIT
        return _CommaDecision.AMBIGUOUS_KEEP

    # An unrecognized phrase that later contains a delta may be either a new event or a
    # continuation.  Keeping it intact is safer, but the caller must know it needs review.
    if _contains_delta(raw_text[right_start:]):
        return _CommaDecision.AMBIGUOUS_KEEP
    return _CommaDecision.KEEP


def _ambiguity_warning(position: int, reason: str) -> _Issue:
    return _Issue(
        position=position,
        warning=DomainWarning(
            code=WarningCode.SEGMENTATION_AMBIGUOUS,
            message_vi=f"Ranh giới tại ký tự {position} chưa chắc chắn: {reason}",
            blocking=True,
        ),
    )


def _implicit_boundary_allowed(
    raw_text: str,
    *,
    current_start: int,
    position: int,
    kind: _EventStartKind,
) -> bool:
    if kind is _EventStartKind.NONE or position <= current_start:
        return False
    if not raw_text[position - 1].isspace():
        return False
    left_text = raw_text[current_start:position]
    if not _contains_delta(left_text):
        return False
    if kind is _EventStartKind.EXPLICIT_DELTA:
        return True
    # A subject/activity/date phrase without its own delta is commonly just the description of
    # the existing event.  Require a second delta before making an implicit split.
    return _contains_delta(_text_before_next_explicit_separator(raw_text, position))


def _text_before_next_explicit_separator(raw_text: str, position: int) -> str:
    """Return the current top-level clause for conservative implicit-boundary checks."""
    urls = _url_spans(raw_text)
    cursor = position
    bracket_depth = 0
    while cursor < len(raw_text):
        url_end = _url_end_at(cursor, urls)
        if url_end is not None:
            cursor = url_end
            continue
        character = raw_text[cursor]
        if character in _OPENING_BRACKETS:
            bracket_depth += 1
        elif character in _CLOSING_BRACKETS:
            bracket_depth = max(0, bracket_depth - 1)
        elif bracket_depth == 0:
            if character in _STRONG_DELIMITERS:
                break
            if character == "," and not is_decimal_comma(raw_text, cursor):
                break
        cursor += 1
    return raw_text[position:cursor]


def _issues_for_segment(
    issues: list[_Issue], start: int, end: int, delimiter_after: str
) -> tuple[DomainWarning, ...]:
    covered_end = end + len(delimiter_after)
    return tuple(
        issue.warning for issue in issues if start <= issue.position < max(end, covered_end)
    )


def segment_evidence(raw_text: str) -> SegmentationResult:
    """Split evidence conservatively while preserving exact spans and delimiters.

    The function is deterministic and side-effect free.  Unknown text is retained.  Strong
    separators split at top level; comma and implicit boundaries require an event-start signal.
    """
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be a string")

    urls = _url_spans(raw_text)
    drafts: list[_SegmentDraft] = []
    issues: list[_Issue] = []
    leading_text = ""
    current_start = _skip_whitespace(raw_text, 0)
    leading_text = raw_text[:current_start]
    position = current_start
    bracket_depth = 0

    def commit_boundary(boundary_start: int, boundary_end: int) -> None:
        nonlocal current_start, leading_text
        segment_start = _skip_whitespace(raw_text, current_start)
        segment_end = _trim_whitespace_left(raw_text, boundary_start, segment_start)
        if segment_start < segment_end:
            drafts.append(
                _SegmentDraft(
                    start=segment_start,
                    end=segment_end,
                    delimiter_after=raw_text[segment_end:boundary_end],
                )
            )
        elif drafts:
            drafts[-1].delimiter_after += raw_text[current_start:boundary_end]
        else:
            leading_text += raw_text[current_start:boundary_end]
        current_start = boundary_end

    while position < len(raw_text):
        url_end = _url_end_at(position, urls)
        if url_end is not None:
            position = url_end
            continue

        character = raw_text[position]
        if character in _OPENING_BRACKETS:
            bracket_depth += 1
            position += 1
            continue
        if character in _CLOSING_BRACKETS:
            bracket_depth = max(0, bracket_depth - 1)
            position += 1
            continue

        if character in _STRONG_DELIMITERS:
            if bracket_depth > 0:
                issues.append(
                    _ambiguity_warning(
                        position,
                        "dấu ngăn mạnh nằm trong ngoặc nên được giữ nguyên để tránh chia quá mức",
                    )
                )
                position += 1
                continue
            delimiter_end, _ = _consume_punctuation_run(raw_text, position)
            delimiter_start = _trim_whitespace_left(raw_text, position, current_start)
            commit_boundary(delimiter_start, delimiter_end)
            position = delimiter_end
            continue

        if character == "," and bracket_depth == 0 and not is_decimal_comma(raw_text, position):
            delimiter_end, strong_found = _consume_punctuation_run(raw_text, position)
            delimiter_start = _trim_whitespace_left(raw_text, position, current_start)
            if strong_found:
                commit_boundary(delimiter_start, delimiter_end)
                position = delimiter_end
                continue
            if delimiter_end < len(raw_text):
                left_text = raw_text[current_start:delimiter_start]
                decision = _comma_decision(raw_text, left_text, delimiter_end)
                if decision is _CommaDecision.SPLIT:
                    commit_boundary(delimiter_start, delimiter_end)
                    position = delimiter_end
                    continue
                if decision is _CommaDecision.AMBIGUOUS_KEEP:
                    issues.append(
                        _ambiguity_warning(
                            position,
                            "dấu phẩy có thể mở đầu sự kiện mới hoặc chỉ nối nội dung hiện tại",
                        )
                    )
            position += 1
            continue

        if bracket_depth == 0 and position > current_start:
            kind = _event_start_kind(raw_text, position)
            if _implicit_boundary_allowed(
                raw_text,
                current_start=current_start,
                position=position,
                kind=kind,
            ):
                delimiter_start = _trim_whitespace_left(raw_text, position, current_start)
                commit_boundary(delimiter_start, position)
                continue

        position += 1

    if bracket_depth > 0:
        issue_position = max(current_start, len(raw_text) - 1)
        issues.append(
            _ambiguity_warning(
                issue_position,
                "ngoặc mở chưa được đóng nên không thể xác định chắc mọi ranh giới",
            )
        )

    final_start = _skip_whitespace(raw_text, current_start)
    final_end = _trim_whitespace_left(raw_text, len(raw_text), final_start)
    if final_start < final_end:
        drafts.append(
            _SegmentDraft(
                start=final_start,
                end=final_end,
                delimiter_after=raw_text[final_end:],
            )
        )
    elif drafts:
        drafts[-1].delimiter_after += raw_text[current_start:]
    else:
        leading_text += raw_text[current_start:]

    segments = tuple(
        EventSegment(
            raw_text=raw_text[draft.start : draft.end],
            source_span=TextSpan(start=draft.start, end=draft.end),
            delimiter_after=draft.delimiter_after,
            warnings=_issues_for_segment(
                issues, draft.start, draft.end, draft.delimiter_after
            ),
        )
        for draft in drafts
    )
    return SegmentationResult(
        raw_text=raw_text,
        leading_text=leading_text,
        segments=segments,
        warnings=tuple(issue.warning for issue in issues),
    )


def event_candidates_from_segments(
    result: SegmentationResult,
    *,
    person_id: str,
    source_cell: RawCell,
) -> tuple[EventCandidate, ...]:
    """Convert lossless segments to source-backed domain event candidates."""
    if source_cell.raw_text != result.raw_text:
        raise ValueError("segmentation raw_text must match the source cell raw_text")
    return tuple(
        EventCandidate(
            person_id=person_id,
            source_cell=source_cell,
            source_span=segment.source_span,
            candidate_index=index,
            raw_text=segment.raw_text,
            parse_source=ParseSource.DETERMINISTIC,
            warnings=segment.warnings,
        )
        for index, segment in enumerate(result.segments)
    )
