"""Public deterministic evidence-segmentation API."""

from point_audit.parsing.segmenter import (
    EventSegment,
    SegmentationResult,
    event_candidates_from_segments,
    is_decimal_comma,
    segment_evidence,
    starts_new_event,
)
from point_audit.parsing.semantic_parser import parse_event_candidate

__all__ = [
    "EventSegment",
    "SegmentationResult",
    "event_candidates_from_segments",
    "is_decimal_comma",
    "parse_event_candidate",
    "segment_evidence",
    "starts_new_event",
]
