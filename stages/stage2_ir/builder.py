import os

from stages.stage1_inventory.models import FileContent
from stages.stage2_ir.bms_ir import build_bms_ir
from stages.stage2_ir.cobol_ir import build_program_ir
from stages.stage2_ir.copybook_ir import build_copybook_ir
from stages.stage2_ir.jcl_ir import build_jcl_ir


def build_file_ir(
    content: FileContent,
    file_type: str,
    rel_path: str,
    declared_names: list[str],
    sha256: str,
) -> dict:
    """Build the header and supported body for one file."""
    header = {
        "schema_version": "1.0",
        "path": rel_path,
        "type": file_type,
        "sha256": sha256,
        "lines": len(content.raw_lines),
        "encoding": content.encoding,
        "source_format": content.source_format,
        "declared_names": declared_names,
        "parse_status": "complete",
        "unparsed_ranges": [],
    }
    builders = {
        "cobol_program": ("program", build_program_ir),
        "jcl": ("jcl", build_jcl_ir),
        "jcl_proc": ("jcl", build_jcl_ir),
        "copybook": ("copybook", build_copybook_ir),
        "bms_map": ("bms", build_bms_ir),
    }
    builder_info = builders.get(file_type)
    if builder_info is None:
        return header

    body_key, builder = builder_info
    try:
        body, unparsed_ranges = builder(content, rel_path, declared_names)
        header[body_key] = body
        header["unparsed_ranges"] = unparsed_ranges
        if unparsed_ranges:
            header["parse_status"] = "partial"
    except Exception as error:
        header["parse_status"] = "partial"
        header["unparsed_ranges"] = [
            {
                "start": 1,
                "end": len(content.raw_lines),
                "reason": f"extractor error: {error}",
            }
        ]
    return header
