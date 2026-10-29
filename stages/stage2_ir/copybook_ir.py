import os
import re

from stages.stage1_inventory.models import FileContent
from stages.stage2_ir.cobol_ir import parse_data_items
from stages.stage2_ir.common import find_exec_blocks

COPY_NAME = re.compile(r"^\s*COPY\s+[\"']?([A-Z0-9][A-Z0-9_-]*)", re.IGNORECASE)
DECLARE_TABLE = re.compile(
    r"\bDECLARE\s+([A-Z0-9_-]+)\s+TABLE\b",
    re.IGNORECASE,
)


def build_copybook_ir(
    content: FileContent,
    rel_path: str,
    declared_names: list[str],
) -> tuple[dict, list[dict]]:
    """Build copybook IR data and return no unparsed ranges."""
    copies = [
        {"name": match.group(1).upper(), "line": line}
        for line, text in content.code_lines
        if (match := COPY_NAME.search(text))
    ]
    declares_table = None
    for block in find_exec_blocks(content.code_lines):
        if block["kind"] == "SQL":
            match = DECLARE_TABLE.search(block["text"])
            if match:
                declares_table = match.group(1).upper()
                break

    stem = os.path.splitext(os.path.basename(rel_path))[0].upper()
    name = declared_names[0] if declared_names else stem
    result = {
        "id": f"cpy:{name}",
        "name": name,
        "copies": copies,
        "data_items": parse_data_items(content.code_lines),
        "declares_table": declares_table,
    }
    return result, []
