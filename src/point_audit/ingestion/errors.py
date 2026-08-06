"""Errors raised while inspecting the source workbook structure."""


class WorkbookIngestionError(Exception):
    """Base error for failures that prevent safe workbook ingestion."""


class WorkbookStructureError(WorkbookIngestionError):
    """The workbook does not have the supported one-sheet structure."""


class HeaderNotFoundError(WorkbookIngestionError):
    """No row contains all required source headers."""


class HeaderAmbiguousError(WorkbookIngestionError):
    """More than one row qualifies as the source header."""


class SourceWorkbookChangedError(WorkbookIngestionError):
    """The source file changed while it was being read."""
