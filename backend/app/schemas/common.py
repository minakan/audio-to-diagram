from enum import StrEnum


class DomainLabel(StrEnum):
    PROGRAMMING = "programming"
    IRRELEVANT = "irrelevant"


class PipelineStatus(StrEnum):
    BUFFERING = "buffering"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    DIAGRAM_PLANNING = "diagram_planning"
    GENERATING_SVG = "generating_svg"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    ERROR = "error"
