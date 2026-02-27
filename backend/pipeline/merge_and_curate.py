"""
Merge NeetCode and Striver problem lists, deduplicate, score, and curate ~200 problems.

Scoring:
- in_neetcode: +2
- in_striver: +2
- in_both: +5 bonus
- solution_count / 3 (from NeetCode data)

Manual override list ensures must-have problems always make the cut.
"""

import json
import re
import logging
from pathlib import Path
from typing import Optional, List, Dict

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"

TARGET_COUNT = 200

# Must-have problems (by slug) — always included regardless of score
MUST_HAVE = {
    "two-sum", "best-time-to-buy-and-sell-stock", "contains-duplicate",
    "valid-anagram", "group-anagrams", "top-k-frequent-elements",
    "valid-palindrome", "3sum", "container-with-most-water",
    "maximum-subarray", "sliding-window-maximum", "longest-substring-without-repeating-characters",
    "minimum-window-substring", "valid-parentheses", "largest-rectangle-in-histogram",
    "binary-search", "search-in-rotated-sorted-array", "koko-eating-bananas",
    "reverse-linked-list", "merge-two-sorted-lists", "linked-list-cycle",
    "lru-cache", "invert-binary-tree", "maximum-depth-of-binary-tree",
    "binary-tree-level-order-traversal", "validate-binary-search-tree",
    "lowest-common-ancestor-of-a-binary-search-tree", "serialize-and-deserialize-binary-tree",
    "implement-trie-prefix-tree", "word-search-ii",
    "merge-k-sorted-lists", "find-median-from-data-stream",
    "combination-sum", "permutations", "subsets", "word-search",
    "number-of-islands", "course-schedule", "clone-graph",
    "climbing-stairs", "coin-change", "longest-increasing-subsequence",
    "longest-common-subsequence", "unique-paths", "edit-distance",
    "jump-game", "merge-intervals", "insert-interval",
    "number-of-1-bits", "counting-bits", "reverse-bits",
}

# NeetCode pattern normalization
PATTERN_NORMALIZE = {
    "Arrays & Hashing": "Arrays & Hashing",
    "Two Pointers": "Two Pointers",
    "Sliding Window": "Sliding Window",
    "Stack": "Stack",
    "Binary Search": "Binary Search",
    "Linked List": "Linked List",
    "Trees": "Trees",
    "Tries": "Tries",
    "Heap / Priority Queue": "Heap / Priority Queue",
    "Backtracking": "Backtracking",
    "Graphs": "Graphs",
    "Advanced Graphs": "Graphs",  # Merge into Graphs
    "1-D Dynamic Programming": "1-D DP",
    "2-D Dynamic Programming": "2-D DP",
    "Greedy": "Greedy",
    "Intervals": "Intervals",
    "Math & Geometry": "Math & Geometry",
    "Bit Manipulation": "Bit Manipulation",
}


def extract_number_from_slug(slug: str) -> Optional[int]:
    """Try to extract LC problem number from a slug. Returns None if not possible."""
    # Some Striver problems don't have numbers in their data
    return None


def merge_and_curate() -> List[dict]:
    """Merge, deduplicate, score, and curate problems."""

    # Load NeetCode data
    neetcode_path = DATA_DIR / "neetcode_raw.json"
    if not neetcode_path.exists():
        logger.error(f"{neetcode_path} not found — run parse_neetcode.py first")
        return []
    neetcode = json.loads(neetcode_path.read_text())
    logger.info(f"Loaded {len(neetcode)} NeetCode problems")

    # Load Striver data
    striver_path = DATA_DIR / "striver_raw.json"
    if not striver_path.exists():
        logger.error(f"{striver_path} not found — run parse_striver.py first")
        return []
    striver = json.loads(striver_path.read_text())
    logger.info(f"Loaded {len(striver)} Striver problems")

    # Index by slug for deduplication
    merged: dict[str, dict] = {}

    # Add NeetCode problems first (they have richer metadata)
    for p in neetcode:
        slug = p["slug"]
        pattern = p.get("pattern", "Unknown")

        # Normalize pattern name
        normalized_pattern = PATTERN_NORMALIZE.get(pattern, pattern)

        merged[slug] = {
            "number": p.get("number"),
            "title": p["title"],
            "slug": slug,
            "leetcode_url": p["leetcode_url"],
            "pattern": normalized_pattern,
            "solution_count": p.get("solution_count", 0),
            "in_neetcode": True,
            "in_striver": False,
            "in_both": False,
        }

    # Add/merge Striver problems
    for p in striver:
        slug = p["slug"]
        if slug in merged:
            # Already in NeetCode — mark overlap
            merged[slug]["in_striver"] = True
            merged[slug]["in_both"] = True
        else:
            # Striver-only problem
            section = p.get("section", "Unknown")
            merged[slug] = {
                "number": p.get("number"),
                "title": p["title"],
                "slug": slug,
                "leetcode_url": p["leetcode_url"],
                "pattern": section,  # Use section as rough pattern
                "solution_count": 0,
                "in_neetcode": False,
                "in_striver": True,
                "in_both": False,
            }

    logger.info(f"\nMerged: {len(merged)} unique problems")
    both_count = sum(1 for p in merged.values() if p["in_both"])
    logger.info(f"  In both sources: {both_count}")
    logger.info(f"  NeetCode only: {sum(1 for p in merged.values() if p['in_neetcode'] and not p['in_striver'])}")
    logger.info(f"  Striver only: {sum(1 for p in merged.values() if p['in_striver'] and not p['in_neetcode'])}")

    # Score each problem
    for slug, p in merged.items():
        score = 0.0
        if p["in_neetcode"]:
            score += 2
        if p["in_striver"]:
            score += 2
        if p["in_both"]:
            score += 5
        score += p.get("solution_count", 0) / 3.0

        # Must-have bonus
        if slug in MUST_HAVE:
            score += 100

        p["score"] = round(score, 2)

    # Sort by score descending, take top TARGET_COUNT
    all_problems = sorted(merged.values(), key=lambda x: -x["score"])
    curated = all_problems[:TARGET_COUNT]

    # Fill in missing numbers — extract from slug if possible, else leave None
    for p in curated:
        if p["number"] is None:
            # Try to look up from the slug later via LeetCode API
            pass

    # Summary
    patterns: dict[str, int] = {}
    for p in curated:
        pat = p["pattern"]
        patterns[pat] = patterns.get(pat, 0) + 1

    logger.info(f"\nCurated: {len(curated)} problems across {len(patterns)} patterns:")
    for pat, count in sorted(patterns.items(), key=lambda x: -x[1]):
        logger.info(f"  {pat}: {count}")

    # Score distribution
    scores = [p["score"] for p in curated]
    logger.info(f"\nScore range: {min(scores):.1f} — {max(scores):.1f}")
    logger.info(f"  Must-have problems included: {sum(1 for p in curated if p['slug'] in MUST_HAVE)}")

    return curated


def run():
    """Main entry point."""
    curated = merge_and_curate()
    if not curated:
        return []

    output_path = DATA_DIR / "curated_problems.json"
    with open(output_path, "w") as f:
        json.dump(curated, f, indent=2)
    logger.info(f"\nSaved {len(curated)} curated problems to {output_path}")

    return curated


if __name__ == "__main__":
    run()
