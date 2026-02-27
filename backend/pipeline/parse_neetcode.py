"""
Parse NeetCode GitHub README to extract patterns and problems.

NeetCode's README has a structure like:
## Pattern Name
| Problem | Solution | ... |
| [XXXX - Title](leetcode-url) | [checkmark] | ... |

We extract each pattern section and all problems within it.
"""

import json
import re
import logging
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

NEETCODE_README_URL = (
    "https://raw.githubusercontent.com/neetcode-gh/leetcode/main/README.md"
)

DATA_DIR = Path(__file__).parent / "data"


def fetch_readme() -> str:
    """Fetch the raw README.md from NeetCode GitHub."""
    logger.info("Fetching NeetCode README from GitHub...")
    resp = requests.get(NEETCODE_README_URL, timeout=30)
    resp.raise_for_status()
    logger.info(f"Fetched {len(resp.text)} characters")
    return resp.text


def parse_problems(readme_text: str) -> list[dict]:
    """
    Parse patterns and problems from the README markdown.

    Returns a list of problem dicts with:
    - number: int (LeetCode problem number)
    - title: str
    - slug: str (from the leetcode URL)
    - leetcode_url: str
    - pattern: str (the section heading)
    - solution_count: int (number of solution checkmarks — proxy for importance)
    """
    problems = []
    current_pattern = None

    # Pattern for section headings like "## Two Pointers" or "### Arrays & Hashing"
    heading_re = re.compile(r"^#{2,3}\s+(.+)$")

    # Pattern for problem rows in markdown tables
    # Matches: | [XXXX - Title](url) | or variations
    problem_re = re.compile(
        r"\[(\d+)\s*[-–.]\s*(.+?)\]\((https?://leetcode\.com/problems/([^/)]+)/?)\)"
    )

    # Checkmark patterns (✅ or links to solutions)
    checkmark_re = re.compile(r"✅|✔|<a\s+href")

    # Patterns to skip (not DSA patterns)
    skip_patterns = {
        "leetcode",
        "neetcode",
        "table of contents",
        "contributing",
        "javascript",
    }

    for line in readme_text.splitlines():
        # Check for section heading
        heading_match = heading_re.match(line.strip())
        if heading_match:
            pattern_name = heading_match.group(1).strip()
            # Skip non-pattern sections
            if pattern_name.lower() not in skip_patterns:
                current_pattern = pattern_name
            continue

        if current_pattern is None:
            continue

        # Check for problem row
        problem_match = problem_re.search(line)
        if problem_match:
            number = int(problem_match.group(1))
            title = problem_match.group(2).strip()
            leetcode_url = problem_match.group(3)
            slug = problem_match.group(4)

            # Count solution checkmarks in this row
            solution_count = len(checkmark_re.findall(line))

            problems.append(
                {
                    "number": number,
                    "title": title,
                    "slug": slug,
                    "leetcode_url": leetcode_url,
                    "pattern": current_pattern,
                    "solution_count": solution_count,
                    "source": "neetcode",
                }
            )

    return problems


def get_pattern_summary(problems: list[dict]) -> dict[str, int]:
    """Get a summary of patterns and their problem counts."""
    patterns: dict[str, int] = {}
    for p in problems:
        pattern = p["pattern"]
        patterns[pattern] = patterns.get(pattern, 0) + 1
    return patterns


def run():
    """Main entry point."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    readme = fetch_readme()
    problems = parse_problems(readme)

    # Summary
    pattern_summary = get_pattern_summary(problems)
    logger.info(f"\nParsed {len(problems)} problems across {len(pattern_summary)} patterns:")
    for pattern, count in sorted(pattern_summary.items(), key=lambda x: -x[1]):
        logger.info(f"  {pattern}: {count} problems")

    # Save
    output_path = DATA_DIR / "neetcode_raw.json"
    with open(output_path, "w") as f:
        json.dump(problems, f, indent=2)
    logger.info(f"\nSaved to {output_path}")

    return problems


if __name__ == "__main__":
    run()
