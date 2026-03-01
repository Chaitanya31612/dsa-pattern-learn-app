"""
Build the final db.json that the frontend consumes.

Merges:
- patterns.json (pattern explanations, templates, triggers)
- enriched_problems.json (curated problems with LeetCode metadata)
- problem_insights.json (per-problem LLM-generated insights)

Output structure:
{
  "patterns": [ { ...pattern data, "problem_slugs": [...] } ],
  "problems": { "slug": { ...all merged problem data } },
  "pattern_order": [ ...recommended learning sequence ]
}
"""

import json
import logging
import re
from html import unescape
from pathlib import Path
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"

# Recommended learning order (from fundamentals to advanced)
PATTERN_ORDER = [
    "arrays-hashing",
    "two-pointers",
    "sliding-window",
    "stack",
    "binary-search",
    "linked-list",
    "trees",
    "tries",
    "heap-priority-queue",
    "backtracking",
    "graphs",
    "1d-dp",
    "2d-dp",
    "greedy",
    "intervals",
    "bit-manipulation",
    "math-geometry",
]

# Map pattern display names to pattern IDs
PATTERN_NAME_TO_ID = {
    "Arrays & Hashing": "arrays-hashing",
    "Two Pointers": "two-pointers",
    "Sliding Window": "sliding-window",
    "Stack": "stack",
    "Binary Search": "binary-search",
    "Linked List": "linked-list",
    "Trees": "trees",
    "Tries": "tries",
    "Heap / Priority Queue": "heap-priority-queue",
    "Backtracking": "backtracking",
    "Graphs": "graphs",
    "1-D DP": "1d-dp",
    "2-D DP": "2d-dp",
    "Greedy": "greedy",
    "Intervals": "intervals",
    "Bit Manipulation": "bit-manipulation",
    "Math & Geometry": "math-geometry",
}


def load_json(filename: str) -> Any:
    """Load a JSON file from the data directory."""
    path = DATA_DIR / filename
    if not path.exists():
        logger.error(f"{path} not found")
        return None
    data = json.loads(path.read_text())
    logger.info(f"Loaded {filename}: {len(data)} items")
    return data


def html_to_text(html: str) -> str:
    """
    Convert LeetCode HTML description to compact plain text.

    Why we do this:
    - The frontend can render a short readable preview without HTML parsing.
    - The AI interviewer can use cleaner context than raw tags.

    Example input:
      "<p>Given an array <code>nums</code>...</p><p><strong>Example 1:</strong></p>"
    Example output:
      "Given an array nums... Example 1:"
    """
    if not html:
        return ""

    # Replace block-ish tags with newlines so sections don't collapse into one line.
    text = re.sub(r"</?(p|div|li|ul|ol|br|pre|code)[^>]*>", "\n", html)
    # Remove remaining tags.
    text = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities (e.g., &nbsp; -> space, &lt; -> <).
    text = unescape(text)
    # Normalize whitespace: multiple spaces/newlines become a single space.
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_db():
    """Build the final database."""

    # Load all data sources
    patterns_raw = load_json("patterns.json")
    enriched = load_json("enriched_problems.json")
    insights_raw = load_json("problem_insights.json")

    if not all([patterns_raw, enriched, insights_raw]):
        logger.error("Missing data files. Run the pipeline steps first.")
        return

    # Index insights by slug
    insights_by_slug: Dict[str, dict] = {}
    for ins in insights_raw:
        slug = ins.get("slug")
        if slug:
            insights_by_slug[slug] = ins

    logger.info(f"Indexed {len(insights_by_slug)} problem insights")

    # Build problems dict — merge enriched data + insights
    problems: Dict[str, dict] = {}
    for p in enriched:
        slug = p["slug"]
        pattern_name = p.get("pattern", "Unknown")
        pattern_id = PATTERN_NAME_TO_ID.get(pattern_name, pattern_name.lower().replace(" ", "-"))

        # Merge enriched problem data
        problem = {
            "number": p.get("number"),
            "title": p.get("title", ""),
            "slug": slug,
            "leetcode_url": p.get("leetcode_url", f"https://leetcode.com/problems/{slug}/"),
            # Keep both forms:
            # - description_html: full fidelity if UI wants rich rendering later.
            # - description_text: prompt-ready text for search/AI context.
            "description_html": p.get("description_html", ""),
            "description_text": html_to_text(p.get("description_html", "")),
            "difficulty": p.get("difficulty"),
            "acceptance_rate": p.get("acceptance_rate"),
            "topic_tags": p.get("topic_tags", []),
            "pattern_id": pattern_id,
            "pattern_name": pattern_name,
            "in_neetcode": p.get("in_neetcode", False),
            "in_striver": p.get("in_striver", False),
            "in_both": p.get("in_both", False),
            "score": p.get("score", 0),
        }

        # Merge LLM-generated insights
        insight = insights_by_slug.get(slug, {})
        problem["pattern_hint"] = insight.get("pattern_hint", "")
        problem["key_insight"] = insight.get("key_insight", "")
        problem["template_deviation"] = insight.get("template_deviation", "")
        problem["common_mistake"] = insight.get("common_mistake", "")
        problem["time_complexity"] = insight.get("time_complexity", p.get("time_complexity", ""))
        problem["space_complexity"] = insight.get("space_complexity", p.get("space_complexity", ""))

        problems[slug] = problem

    logger.info(f"Built {len(problems)} problems")

    # Build patterns list — attach problem slugs to each pattern
    patterns: List[dict] = []
    for pat in patterns_raw:
        pattern_id = pat.get("pattern_id", "")

        # Find all problems belonging to this pattern
        problem_slugs = sorted(
            [slug for slug, p in problems.items() if p["pattern_id"] == pattern_id],
            key=lambda s: -(problems[s].get("score", 0))  # Sort by score descending
        )

        pattern_entry = {
            "pattern_id": pattern_id,
            "name": pat.get("name", ""),
            "explanation": pat.get("explanation", ""),
            "mental_model": pat.get("mental_model", ""),
            "template_code_python": pat.get("template_code_python", ""),
            "template_code_javascript": pat.get("template_code_javascript", ""),
            "template_code_java": pat.get("template_code_java", ""),
            "trigger_phrases": pat.get("trigger_phrases", []),
            "when_to_use": pat.get("when_to_use", []),
            "common_mistakes": pat.get("common_mistakes", []),
            "time_complexity": pat.get("time_complexity", ""),
            "space_complexity": pat.get("space_complexity", ""),
            "related_patterns": pat.get("related_patterns", []),
            "sample_walkthrough": pat.get("sample_walkthrough", {}),
            "problem_count": len(problem_slugs),
            "problem_slugs": problem_slugs,
        }
        patterns.append(pattern_entry)

    # Sort patterns by recommended learning order
    pattern_id_order = {pid: i for i, pid in enumerate(PATTERN_ORDER)}
    patterns.sort(key=lambda p: pattern_id_order.get(p["pattern_id"], 999))

    logger.info(f"Built {len(patterns)} patterns")

    # Difficulty distribution
    diff_dist = {}
    for p in problems.values():
        d = p.get("difficulty", "Unknown") or "Unknown"
        diff_dist[d] = diff_dist.get(d, 0) + 1
    logger.info(f"Difficulty distribution: {diff_dist}")

    # Pattern distribution
    for pat in patterns:
        logger.info(f"  {pat['name']}: {pat['problem_count']} problems")

    # Assemble final DB
    db = {
        "patterns": patterns,
        "problems": problems,
        "pattern_order": PATTERN_ORDER,
        "meta": {
            "total_problems": len(problems),
            "total_patterns": len(patterns),
            "difficulty_distribution": diff_dist,
        },
    }

    # Save
    output_path = DATA_DIR / "db.json"
    with open(output_path, "w") as f:
        json.dump(db, f, indent=2)

    # File size
    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"\nSaved db.json ({size_mb:.1f} MB) to {output_path}")

    # Validation
    assert len(db["patterns"]) >= 15, f"Too few patterns: {len(db['patterns'])}"
    assert len(db["problems"]) >= 180, f"Too few problems: {len(db['problems'])}"
    logger.info("✓ Validation passed")

    return db


def run():
    """Main entry point."""
    build_db()


if __name__ == "__main__":
    run()
