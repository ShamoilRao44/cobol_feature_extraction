from stages.stage1_inventory.models import Classification, FileContent
from stages.stage1_inventory.scorers import (
    SCORERS,
    looks_like_markdown,
    score_documentation,
)


def decide_type(scores: dict[str, int]) -> tuple[str, str, str | None]:
    """Choose a type, confidence, and positive-scoring runner-up."""
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    if not ranked:
        return "unknown", "low", None

    top_name, top_score = ranked[0]
    second_name, second_score = ranked[1] if len(ranked) > 1 else (None, 0)
    if top_score < 5:
        return "unknown", "low", top_name if top_score > 0 else None

    runner_up = second_name if second_score > 0 else None
    margin = top_score - second_score
    if top_score >= 8 and margin >= 4:
        confidence = "high"
    elif top_score >= 5 and margin >= 2:
        confidence = "medium"
    else:
        confidence = "low"
    return top_name, confidence, runner_up


def classify(content: FileContent) -> Classification:
    """Classify file content using its kind and code lines."""
    if content.kind in {"too_large", "binary"}:
        return Classification(
            content.kind,
            "high",
            [f"kind: {content.kind}"],
            None,
            {},
        )

    if not any(line.strip() for line in content.raw_lines):
        return Classification("empty", "high", [], None, {})

    if looks_like_markdown(content.code_lines):
        score, evidence = score_documentation(content.code_lines)
        return Classification(
            "documentation",
            "high",
            evidence,
            None,
            {"documentation": score},
        )

    results = {
        file_type: scorer(content.code_lines)
        for file_type, scorer in SCORERS.items()
    }
    all_scores = {file_type: result[0] for file_type, result in results.items()}
    file_type, confidence, runner_up = decide_type(all_scores)
    top_type = min(all_scores, key=lambda name: (-all_scores[name], name))
    evidence = results[top_type][1] if all_scores[top_type] > 0 else []

    return Classification(
        file_type,
        confidence,
        evidence,
        runner_up,
        {name: score for name, score in all_scores.items() if score > 0},
    )
