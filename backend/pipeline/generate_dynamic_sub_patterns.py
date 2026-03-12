"""
Generate optimal, granular sub-patterns dynamically using Groq.

Reads `enriched_problems.json`, groups by major patterns, and asks the AI to deduce
the most logical sub-pattern categorization.

Outputs: `data/dynamic_sub_patterns.json`
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

from dotenv import load_dotenv

# Load .env
load_dotenv(Path(__file__).parent.parent / ".env")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ai import AIAnalyzerFactory, AIProvider

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"

BATCH_DELAY = 10 # Delay to respect Groq rate limits

SCHEMA = """{
  "sub_patterns": [
    {
      "sub_pattern_id": "string - kebab case id (e.g. monotonic-stack-next-greater)",
      "name": "string - human readable name",
      "description": "string - 1 to 2 sentence description on what distinguishes this from others",
      "trigger_phrases": ["list of exact indicator words in a problem prompt"],
      "problem_slugs": ["list of problem slugs belonging to this sub pattern"]
    }
  ]
}"""

# 17 Main patterns
PATTERNS = [
    "Arrays & Hashing", "Two Pointers", "Sliding Window", "Stack",
    "Binary Search", "Linked List", "Trees", "Tries", "Heap / Priority Queue",
    "Backtracking", "Graphs", "1-D DP", "2-D DP", "Greedy", "Intervals",
    "Bit Manipulation", "Math & Geometry"
]

def map_pattern_name_to_id(name: str) -> str:
    mapping = {
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
    return mapping.get(name, name.lower().replace(" ", "-"))


def build_prompt(pattern_name: str, problems: List[dict]) -> str:
    problem_list = "\\n".join(
        f"- Slug: {p['slug']} | Title: {p['title']} | Difficulty: {p.get('difficulty', '?')}"
        for p in problems
    )

    return f"""You are a DSA Curriculum Architect. I am giving you a list of LeetCode problems
that all belong to the parent pattern: "{pattern_name}".

Your goal is to divide these specific problems into 2 to 6 optimal, highly cohesive "Sub-Patterns".
Do not create generic sub-patterns—base them strictly on the problems provided below.
Ensure EVERY problem slug listed below is assigned to exactly one sub-pattern.

Problems:
{problem_list}

Return a valid JSON object following this exact schema:
{SCHEMA}

Important:
- Return ONLY valid JSON, without any markdown formatting block, introduction, or explanation.
- Ensure all problem_slugs exactly match the list provided."""

def generate_sub_patterns_for_pattern(analyzer, pattern_name: str, problems: List[dict], max_retries: int = 3) -> List[Dict[str, Any]]:
    if not problems:
        return []

    prompt = build_prompt(pattern_name, problems)

    for attempt in range(max_retries):
        try:
            response = analyzer.analyze(
                content=prompt,
                prompt="You are an expert curriculum developer. Output raw valid JSON only.",
            )

            if not response.success:
                logger.warning(f"  Attempt {attempt + 1} failed: {response.error}")
                time.sleep(2 ** attempt)
                continue

            text = response.content.strip()
            if text.startswith("```"):
                text = text.split("\\n", 1)[1]
                if text.endswith("```"):
                    text = text[:-3]
                elif "```" in text:
                    text = text[:text.rfind("```")]
            text = text.strip()

            data = json.loads(text)
            sub_patterns = data.get("sub_patterns", [])

            if not isinstance(sub_patterns, list):
                raise ValueError("JSON must contain 'sub_patterns' list.")

            logger.info(f"  ✓ Generated {len(sub_patterns)} sub-patterns for {pattern_name}")
            return sub_patterns

        except json.JSONDecodeError as e:
            logger.warning(f"  Attempt {attempt + 1} JSON parse error: {e}")
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.warning(f"  Attempt {attempt + 1} error: {e}")
            time.sleep(2 ** attempt)

    logger.error(f"  ✗ Failed for {pattern_name} after {max_retries} attempts.")
    return []

def run():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    enriched_path = DATA_DIR / "enriched_problems.json"

    if not enriched_path.exists():
        logger.error(f"{enriched_path} missing.")
        return

    problems = json.loads(enriched_path.read_text())

    # Group problems by pattern
    problems_by_pattern = {p: [] for p in PATTERNS}
    for p in problems:
        p_name = p.get("pattern")
        if p_name in problems_by_pattern:
            problems_by_pattern[p_name].append(p)

    out_path = DATA_DIR / "dynamic_sub_patterns.json"
    existing = {}
    if out_path.exists():
        existing = json.loads(out_path.read_text())
        logger.info(f"Resuming with {len(existing)} patterns already generated.")

    analyzer = AIAnalyzerFactory.create(AIProvider.GROQ, model="smart")
    logger.info(f"Using: {analyzer.provider.value} ({analyzer.model_name})")

    results = existing.copy()

    for i, pattern_name in enumerate(PATTERNS, 1):
        pattern_id = map_pattern_name_to_id(pattern_name)

        if pattern_id in results and results[pattern_id]:
            logger.info(f"[{i}/{len(PATTERNS)}] Skipping {pattern_name} (already cached).")
            continue

        pattern_problems = problems_by_pattern.get(pattern_name, [])
        logger.info(f"[{i}/{len(PATTERNS)}] Generating sub-patterns for {pattern_name} ({len(pattern_problems)} problems)...")

        sub_patterns = generate_sub_patterns_for_pattern(analyzer, pattern_name, pattern_problems)

        # Save output
        results[pattern_id] = sub_patterns
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)

        if i < len(PATTERNS):
            time.sleep(BATCH_DELAY)

    logger.info(f"\\nDone! Saved all to {out_path}")

if __name__ == "__main__":
    run()
