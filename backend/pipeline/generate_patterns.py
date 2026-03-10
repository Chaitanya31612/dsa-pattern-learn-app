"""
Generate pattern explanations, templates, and metadata using the AI factory.

For each of the ~16 patterns, generates structured JSON with:
- explanation, mental_model, template_code (Python + JS)
- trigger_phrases, when_to_use, common_mistakes
- time/space complexity, related_patterns
- sample_walkthrough with a canonical problem

Uses the existing ai/ module via AIAnalyzerFactory.
"""

import json
import sys
import time
import logging
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv
from sub_patterns import get_sub_patterns_for_pattern

# Load .env from backend root
load_dotenv(Path(__file__).parent.parent / ".env")

from ai import AIAnalyzerFactory, AIProvider

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"

# Pattern definitions with canonical problems for context
PATTERNS = [
    {"id": "arrays-hashing", "name": "Arrays & Hashing"},
    {"id": "two-pointers", "name": "Two Pointers"},
    {"id": "sliding-window", "name": "Sliding Window"},
    {"id": "stack", "name": "Stack"},
    {"id": "binary-search", "name": "Binary Search"},
    {"id": "linked-list", "name": "Linked List"},
    {"id": "trees", "name": "Trees"},
    {"id": "tries", "name": "Tries"},
    {"id": "heap-priority-queue", "name": "Heap / Priority Queue"},
    {"id": "backtracking", "name": "Backtracking"},
    {"id": "graphs", "name": "Graphs"},
    {"id": "1d-dp", "name": "1-D DP"},
    {"id": "2d-dp", "name": "2-D DP"},
    {"id": "greedy", "name": "Greedy"},
    {"id": "intervals", "name": "Intervals"},
    {"id": "bit-manipulation", "name": "Bit Manipulation"},
    {"id": "math-geometry", "name": "Math & Geometry"},
]

OUTPUT_SCHEMA = """{
  "pattern_id": "string - kebab-case ID",
  "name": "string - display name",
  "explanation": "string - 2-3 paragraph explanation of the pattern",
  "mental_model": "string - one sentence mental model",
  "template_code_python": "string - Python template implementing the pattern",
  "template_code_javascript": "string - JavaScript template implementing the pattern",
  "template_code_java": "string - Java template implementing the pattern",
  "trigger_phrases": ["list of 5-8 phrases that signal this pattern"],
  "when_to_use": ["list of 4-6 bullet points on when to apply this pattern"],
  "common_mistakes": ["list of 3-5 common mistakes when using this pattern"],
  "time_complexity": "string - typical time complexity",
  "space_complexity": "string - typical space complexity",
  "related_patterns": ["list of 2-4 related pattern IDs"],
  "sub_patterns": [
    {
      "sub_pattern_id": "string - kebab-case unique under this pattern",
      "name": "string - display name",
      "description": "string - when/why this sub-pattern is used",
      "trigger_phrases": ["list of 3-6 phrases specific to this sub-pattern"]
    }
  ],
  "sample_walkthrough": {
    "problem": "string - canonical problem name",
    "problem_number": "int - LeetCode problem number",
    "approach": "string - step-by-step walkthrough showing how the pattern applies"
  }
}"""


def get_problems_for_pattern(enriched: List[dict], pattern_name: str) -> List[dict]:
    """Get the problem titles for a pattern to give the LLM context."""
    problems = [p for p in enriched if p.get("pattern") == pattern_name]
    return problems[:10]  # Top 10 by score for context


def generate_pattern_prompt(pattern: dict, problems: List[dict]) -> str:
    """Build the prompt for generating a pattern explanation."""
    problem_list = "\n".join(
        f"  - #{p.get('number', '?')} {p['title']} ({p.get('difficulty', '?')})"
        for p in problems
    )

    sub_pattern_schema = json.dumps(get_sub_patterns_for_pattern(pattern["id"]), indent=2)

    return f"""You are a DSA teaching expert. Generate a comprehensive learning resource for the "{pattern['name']}" pattern.

Here are some canonical problems that use this pattern:
{problem_list}

Use the following sub-pattern taxonomy for this pattern exactly as-is:
{sub_pattern_schema}

Generate a JSON object with the following schema:
{OUTPUT_SCHEMA}

Important:
- The pattern_id should be "{pattern['id']}"
- The name should be "{pattern['name']}"
- The explanation should be thorough but accessible, aimed at someone preparing for coding interviews
- Template code should be clean, well-commented, and use standard patterns
- Trigger phrases should be specific words/phrases from problem statements that signal this pattern
- Keep `sub_patterns` aligned with the provided taxonomy IDs and names
- The sample walkthrough should use one of the listed problems
- related_patterns should reference IDs from: {', '.join(p['id'] for p in PATTERNS)}
- Return ONLY the JSON, no markdown fences or extra text"""


def generate_single_pattern(
    analyzer,
    pattern: dict,
    problems: List[dict],
    max_retries: int = 3,
) -> Dict[str, Any]:
    """Generate content for a single pattern with retries."""
    prompt = generate_pattern_prompt(pattern, problems)

    for attempt in range(max_retries):
        try:
            response = analyzer.analyze(
                content=prompt,
                prompt="You are a DSA expert and a good teacher who recognize patterns in things and can explain them well. Return only valid JSON.",
            )

            if not response.success:
                logger.warning(f"  Attempt {attempt + 1} failed: {response.error}")
                time.sleep(2 ** attempt)
                continue

            # Try to parse JSON
            text = response.content.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text[:-3]
                elif "```" in text:
                    text = text[:text.rfind("```")]
            text = text.strip()

            data = json.loads(text)

            # Validate required fields
            required = ["explanation", "mental_model", "template_code_python", "trigger_phrases"]
            missing = [f for f in required if f not in data]
            if missing:
                logger.warning(f"  Missing fields: {missing}, retrying...")
                time.sleep(2 ** attempt)
                continue

            # Ensure IDs are correct
            data["pattern_id"] = pattern["id"]
            data["name"] = pattern["name"]
            # Keep sub-pattern taxonomy deterministic across regenerations.
            data["sub_patterns"] = get_sub_patterns_for_pattern(pattern["id"])

            logger.info(f"  ✓ Generated {pattern['name']} "
                       f"(tokens: {response.tokens_used}, provider: {response.provider.value})")
            return data

        except json.JSONDecodeError as e:
            logger.warning(f"  Attempt {attempt + 1} JSON parse error: {e}")
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.warning(f"  Attempt {attempt + 1} unexpected error: {e}")
            time.sleep(2 ** attempt)

    # Return a minimal fallback
    logger.error(f"  ✗ Failed to generate {pattern['name']} after {max_retries} attempts")
    return {
        "pattern_id": pattern["id"],
        "name": pattern["name"],
        "explanation": f"Pattern: {pattern['name']}. Content generation failed — please regenerate.",
        "mental_model": "",
        "template_code_python": "",
        "template_code_javascript": "",
        "trigger_phrases": [],
        "when_to_use": [],
        "common_mistakes": [],
        "time_complexity": "",
        "space_complexity": "",
        "related_patterns": [],
        "sub_patterns": get_sub_patterns_for_pattern(pattern["id"]),
        "sample_walkthrough": {"problem": "", "problem_number": 0, "approach": ""},
        "_generation_failed": True,
    }


def run():
    """Main entry point."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Load enriched problems for context
    enriched_path = DATA_DIR / "enriched_problems.json"
    if not enriched_path.exists():
        logger.error(f"{enriched_path} not found — run fetch_leetcode.py first")
        return

    enriched = json.loads(enriched_path.read_text())
    logger.info(f"Loaded {len(enriched)} enriched problems for context")

    # Load existing patterns (for resume support)
    output_path = DATA_DIR / "patterns.json"
    existing_patterns = {}
    if output_path.exists():
        for p in json.loads(output_path.read_text()):
            if not p.get("_generation_failed"):
                existing_patterns[p["pattern_id"]] = p
        logger.info(f"Resuming: {len(existing_patterns)} patterns already generated")

    # Initialize AI
    analyzer = AIAnalyzerFactory.create_default()
    logger.info(f"Using AI provider: {analyzer.provider.value} ({analyzer.model_name})")

    all_patterns = []
    generated_count = 0

    for i, pattern in enumerate(PATTERNS):
        if pattern["id"] in existing_patterns:
            logger.info(f"[{i+1}/{len(PATTERNS)}] Skipping {pattern['name']} (already generated)")
            all_patterns.append(existing_patterns[pattern["id"]])
            continue

        logger.info(f"[{i+1}/{len(PATTERNS)}] Generating {pattern['name']}...")

        # Get relevant problems for context
        problems = get_problems_for_pattern(enriched, pattern["name"])

        # Generate
        data = generate_single_pattern(analyzer, pattern, problems)
        all_patterns.append(data)
        generated_count += 1

        # Save after each pattern for resume support
        with open(output_path, "w") as f:
            json.dump(all_patterns, f, indent=2)

        # Small delay between API calls
        if i < len(PATTERNS) - 1:
            time.sleep(2)

    logger.info(f"\nDone! Generated {generated_count} patterns ({len(all_patterns)} total)")
    logger.info(f"Saved to {output_path}")

    # Summary
    failed = [p for p in all_patterns if p.get("_generation_failed")]
    if failed:
        logger.warning(f"Failed patterns: {[p['name'] for p in failed]}")


if __name__ == "__main__":
    run()
