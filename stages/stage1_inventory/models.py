from dataclasses import dataclass


@dataclass
class FileContent:
    path: str
    kind: str
    encoding: str | None
    line_ending: str
    source_format: str | None
    raw_lines: list[str]
    code_lines: list[tuple[int, str]]


@dataclass
class Classification:
    file_type: str
    confidence: str
    evidence: list[str]
    runner_up: str | None
    scores: dict[str, int]
