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
from sub_patterns import SUB_PATTERN_KEYWORDS, get_sub_patterns_for_pattern

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


def normalize_sub_patterns(raw_sub_patterns: Any, pattern_id: str) -> List[dict]:
    """Normalize optional raw sub-patterns and fallback to configured defaults."""
    normalized: List[dict] = []

    if isinstance(raw_sub_patterns, list):
        for item in raw_sub_patterns:
            if not isinstance(item, dict):
                continue
            sub_pattern_id = str(item.get("sub_pattern_id", "")).strip()
            name = str(item.get("name", "")).strip()
            if not sub_pattern_id or not name:
                continue
            normalized.append({
                "sub_pattern_id": sub_pattern_id,
                "name": name,
                "description": item.get("description", ""),
                "trigger_phrases": item.get("trigger_phrases", []),
            })

    if normalized:
        return normalized

    return get_sub_patterns_for_pattern(pattern_id)


def classify_sub_pattern(problem: dict, sub_patterns: List[dict]) -> dict:
    """
    Heuristically classify a problem into one sub-pattern.
    Uses the AI-generated trigger_phrases from the sub-pattern itself.
    """
    # Filter out parent pattern entries (those without sub_pattern_id)
    valid_subs = [s for s in sub_patterns if s.get("sub_pattern_id")]
    
    if not valid_subs:
        return {"sub_pattern_id": "", "name": ""}

    title_text = str(problem.get("title", "")).lower()
    tags_text = " ".join(str(tag).lower() for tag in problem.get("topic_tags", []))
    desc_text = html_to_text(problem.get("description_html", "")).lower()

    best = valid_subs[0]
    best_score = -1
    
    for sub in valid_subs:
        # Use the AI-generated trigger_phrases
        keywords = sub.get("trigger_phrases", [])
        score = 0
        for kw in keywords:
            token = kw.lower()
            if token in title_text:
                score += 5  # Increased weight for specific AI phrases
            if token in tags_text:
                score += 3
            if token in desc_text:
                score += 1
        
        if score > best_score:
            best_score = score
            best = sub

    return {
        "sub_pattern_id": best.get("sub_pattern_id", ""),
        "name": best.get("name", ""),
    }


def build_db():
    """Build the final database."""

    # Load all data sources
    patterns_raw = load_json("patterns.json")
    enriched = load_json("enriched_problems.json")
    insights_raw = load_json("problem_insights.json")
    company_frequency_path = DATA_DIR / "company_frequency.json"
    if company_frequency_path.exists():
        company_frequency_raw = load_json("company_frequency.json") or {}
    else:
        company_frequency_raw = {}
        logger.info("company_frequency.json not found — continuing without company metadata")
    solution_breakdowns_path = DATA_DIR / "solution_breakdowns.json"
    if solution_breakdowns_path.exists():
        solution_breakdowns_raw = load_json("solution_breakdowns.json") or {}
    else:
        solution_breakdowns_raw = {}
        logger.info("solution_breakdowns.json not found — continuing without solution breakdowns")

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
    company_by_slug = {}
    if isinstance(company_frequency_raw, dict):
        company_by_slug = company_frequency_raw.get("problems", {})
    logger.info(f"Indexed {len(company_by_slug)} company-frequency rows")
    breakdown_by_slug = {}
    if isinstance(solution_breakdowns_raw, dict):
        breakdown_by_slug = solution_breakdowns_raw.get("problems", {})
    logger.info(f"Indexed {len(breakdown_by_slug)} solution breakdown rows")

    # Normalize pattern-level sub-pattern schemas first so they can be used
    # while building per-problem records.
    pattern_metadata: Dict[str, dict] = {} # Overarching pattern info
    pattern_sub_patterns: Dict[str, List[dict]] = {} # Detailed sub-patterns
    
    for item in patterns_raw:
        pid = item.get("pattern_id", "")
        sid = item.get("sub_pattern_id", "")
        if not pid: continue
        
        if not sid:
            # This is a parent pattern entry
            pattern_metadata[pid] = item
        else:
            # This is a sub-pattern entry
            if pid not in pattern_sub_patterns:
                pattern_sub_patterns[pid] = []
            pattern_sub_patterns[pid].append(item)

    # Build problems dict — merge enriched data + insights
    problems: Dict[str, dict] = {}
    for p in enriched:
        slug = p["slug"]
        pattern_name = p.get("pattern", "Unknown")
        pattern_id = PATTERN_NAME_TO_ID.get(pattern_name, pattern_name.lower().replace(" ", "-"))
        sub_pattern = classify_sub_pattern(p, pattern_sub_patterns.get(pattern_id, []))

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
            "sub_pattern_id": sub_pattern.get("sub_pattern_id", ""),
            "sub_pattern_name": sub_pattern.get("name", ""),
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

        # Merge company-frequency metadata (Phase 4)
        freq = company_by_slug.get(slug, {}) if isinstance(company_by_slug, dict) else {}
        problem["companies"] = freq.get("companies", [])
        problem["frequency_tier"] = freq.get("frequency_tier", "low")
        problem["last_seen"] = freq.get("last_seen", "")
        problem["follow_ups"] = freq.get("follow_ups", [])
        problem["source_signals"] = freq.get("source_signals", [])
        problem["interview_lists_count"] = freq.get("interview_lists_count", 0)
        problem["company_count"] = freq.get("company_count", len(problem["companies"]))
        breakdown = breakdown_by_slug.get(slug, {}) if isinstance(breakdown_by_slug, dict) else {}
        if isinstance(breakdown, dict) and breakdown:
            problem["solution_breakdown"] = breakdown

        problems[slug] = problem

    logger.info(f"Built {len(problems)} problems")

    # Build patterns list — attach problem slugs to each pattern
    patterns: List[dict] = []

    # Reverse map ID to Name
    ID_TO_NAME = {v: k for k, v in PATTERN_NAME_TO_ID.items()}

    for pattern_id in PATTERN_ORDER:
        sub_patterns = pattern_sub_patterns.get(pattern_id, [])
        pattern_name = ID_TO_NAME.get(pattern_id, pattern_id.replace("-", " ").title())

        # Find all problems belonging to this pattern
        problem_slugs = sorted(
            [slug for slug, p in problems.items() if p["pattern_id"] == pattern_id],
            key=lambda s: -(problems[s].get("score", 0))  # Sort by score descending
        )

        sub_pattern_entries = []
        for sub in sub_patterns:
            sub_pattern_id = sub.get("sub_pattern_id", "")
            sub_problem_slugs = sorted(
                [
                    slug for slug in problem_slugs
                    if problems[slug].get("sub_pattern_id") == sub_pattern_id
                ],
                key=lambda s: -(problems[s].get("score", 0)),
            )
            sub_pattern_entries.append({
                "sub_pattern_id": sub_pattern_id,
                "name": sub.get("name", ""),
                "description": sub.get("description", ""),
                "trigger_phrases": sub.get("trigger_phrases", []),
                "problem_count": len(sub_problem_slugs),
                "problem_slugs": sub_problem_slugs,
                "explanation": sub.get("explanation", ""),
                "mental_model": sub.get("mental_model", ""),
                "template_code_java": sub.get("template_code_java", "")
            })

        company_counter: Dict[str, int] = {}
        for slug in problem_slugs:
            for company in problems[slug].get("companies", []):
                company_counter[company] = company_counter.get(company, 0) + 1
        top_companies = sorted(
            [{"company": company, "count": count} for company, count in company_counter.items()],
            key=lambda row: (-row["count"], row["company"]),
        )[:5]

        # Use the metadata from patterns.json for the parent pattern
        meta = pattern_metadata.get(pattern_id, {})
        
        pattern_entry = {
            "pattern_id": pattern_id,
            "name": pattern_name,
            "explanation": meta.get("explanation", f"This is the overarching pattern for {pattern_name}."),
            "mental_model": meta.get("mental_model", "See sub-patterns for specific mental models."),
            "template_code_python": meta.get("template_code_python", ""),
            "template_code_javascript": meta.get("template_code_javascript", ""),
            "template_code_java": meta.get("template_code_java", ""),
            "trigger_phrases": meta.get("trigger_phrases", []),
            "when_to_use": meta.get("when_to_use", []),
            "common_mistakes": meta.get("common_mistakes", []),
            "time_complexity": meta.get("time_complexity", ""),
            "space_complexity": meta.get("space_complexity", ""),
            "related_patterns": meta.get("related_patterns", []),
            "sub_patterns": sub_pattern_entries,
            "top_companies": top_companies,
            "sample_walkthrough": meta.get("sample_walkthrough", {}),
            "problem_count": len(problem_slugs),
            "problem_slugs": problem_slugs,
        }

        # Only add pattern if it has problems
        if problem_slugs:
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
            "company_frequency_enabled": bool(company_by_slug),
            "solution_breakdowns_enabled": bool(breakdown_by_slug),
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
