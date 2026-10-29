import os
import re

from stages.stage1_inventory.models import FileContent

MAPSET = re.compile(r"^([A-Z0-9#@$]+)\s+DFHMSD\b", re.IGNORECASE)
MAP = re.compile(
    r"^([A-Z0-9#@$]+)\s+DFHMDI\b(.*)",
    re.IGNORECASE,
)
MAP_SIZE = re.compile(r"\bSIZE\s*=\s*\((\d+)\s*,\s*(\d+)\)", re.IGNORECASE)
FIELD = re.compile(r"\bDFHMDF\b", re.IGNORECASE)


def build_bms_ir(
    content: FileContent,
    rel_path: str,
    declared_names: list[str],
) -> tuple[dict, list[dict]]:
    """Build a BMS map IR record."""
    mapset = None
    maps = []
    field_count = 0
    for line_number, line in enumerate(content.raw_lines, start=1):
        if line.startswith("*"):
            continue
        mapset_match = MAPSET.search(line)
        if mapset_match and mapset is None:
            mapset = mapset_match.group(1).upper()
        map_match = MAP.search(line)
        if map_match:
            size_match = MAP_SIZE.search(map_match.group(2))
            size = (
                f"{size_match.group(1)}x{size_match.group(2)}"
                if size_match
                else None
            )
            maps.append(
                {
                    "name": map_match.group(1).upper(),
                    "size": size,
                    "line": line_number,
                }
            )
        if FIELD.search(line):
            field_count += 1

    stem = os.path.splitext(os.path.basename(rel_path))[0].upper()
    result = {
        "id": f"map:{mapset or stem}",
        "mapset": mapset,
        "maps": maps,
        "field_count": field_count,
    }
    if mapset is None:
        return result, [{"start": 1, "end": len(content.raw_lines), "reason": "no DFHMSD"}]
    return result, []
