import json

RULE_KINDS = {"validation", "calculation", "decision", "data_access", "error_handling", "flow", "other"}
CONFIDENCES = {"high", "medium", "low"}

SYSTEM_PROMPT = (
    "You are a mainframe COBOL analyst. You extract business rules from COBOL code "
    "and explain them in plain English for people who do not read COBOL. "
    "Only state what the code shows. Never invent rules. Reply with JSON only."
)

INSTRUCTIONS = """List the business rules in the COBOL lines below.
A business rule is a check, calculation, decision or data update that matters to the
business (for example "an account with status C cannot be debited"). Skip pure technical
steps (opening files, moving fields for display) unless they decide what happens next.

Reply with exactly this JSON shape and nothing else:
{"rules": [{
  "paragraph": "<paragraph name>",
  "title": "<short name, max 10 words>",
  "description": "<plain English, 1-3 sentences>",
  "kind": "validation|calculation|decision|data_access|error_handling|flow|other",
  "condition": "<when it applies, plain English, or null>",
  "data": ["<COBOL data names, tables or files involved>"],
  "line_start": <first line number>,
  "line_end": <last line number>,
  "confidence": "high|medium|low"
}]}
Use only line numbers shown below. Return {"rules": []} if there are none."""


def program_context(program: dict) -> dict:
    """Summarize the program-level facts sent with every chunk."""
    return {
        "program": program["name"],
        "mode": "online (CICS)" if program.get("dialect", {}).get("uses_cics") else "batch",
        "header_comment": (program.get("header_comment") or "")[:600] or None,
        "parameters": program.get("linkage", {}).get("params", []),
        "files": [
            {"name": f["logical_name"], "ddname": f.get("ddname"), "access": f.get("access")}
            for f in program.get("files", [])
        ],
        "tables": sorted({t for s in program.get("sql", []) for t in s.get("tables", [])}),
    }


def build_prompt(context: dict, facts: dict, source: list[tuple[int, str]]) -> str:
    """Build the user prompt for one chunk."""
    numbered = "\n".join(f"{number:>6} | {text}" for number, text in source)
    return (
        f"{INSTRUCTIONS}\n\n"
        f"PROGRAM FACTS (from a parser, trustworthy):\n{json.dumps(context, indent=1)}\n\n"
        f"FACTS FOR THESE LINES:\n{json.dumps(facts, indent=1)}\n\n"
        f"COBOL LINES:\n{numbered}\n"
    )


def parse_rules(text: str) -> list[dict]:
    """Parse the LLM reply into a list of raw rule dicts."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end < start:
        raise ValueError("LLM reply contains no JSON object")
    data = json.loads(text[start:end + 1])
    rules = data.get("rules") if isinstance(data, dict) else None
    if not isinstance(rules, list):
        raise ValueError("LLM reply has no 'rules' list")
    return [rule for rule in rules if isinstance(rule, dict)]
