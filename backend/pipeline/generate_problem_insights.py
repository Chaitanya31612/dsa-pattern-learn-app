"""
Generate per-problem insights using the AI factory.

For each of the ~200 curated problems, generates:
- pattern_hint: what in the problem signals the pattern
- key_insight: the core idea to solve it
- template_deviation: how to adapt the standard template
- common_mistake: most frequent error
- time/space complexity

Batches 5 problems per API call for Groq TPM limits (~40 calls).
Uses Groq llama-3.3-70b-versatile via the AI factory.
"""

import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv

# Load .env from backend root
load_dotenv(Path(__file__).parent.parent / ".env")

from ai import AIAnalyzerFactory, AIProvider

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"

BATCH_SIZE = 5   # Reduced for Groq 12K TPM limit (~1,500 tokens/batch)
BATCH_DELAY = 20  # Seconds between batches (~3/min within 12K TPM)

INSIGHT_SCHEMA = """{
  "insights": [
    {
      "slug": "string - problem slug (must match input)",
      "pattern_hint": "string - What in the problem tells you to use this pattern (1-2 sentences)",
      "key_insight": "string - Core idea or trick to solve it (1-2 sentences)",
      "template_deviation": "string - How this differs from the standard pattern template (1 sentence)",
      "common_mistake": "string - Most frequent error people make (1 sentence)",
      "time_complexity": "string - e.g. O(n), O(n log n)",
      "space_complexity": "string - e.g. O(1), O(n)"
    }
  ]
}"""


def build_batch_prompt(problems: List[dict]) -> str:
    """Build prompt for a batch of problems."""
    problem_descriptions = []
    for p in problems:
        desc = (
            f"- #{p.get('number', '?')} \"{p['title']}\" (slug: {p['slug']}, "
            f"pattern: {p.get('pattern', '?')}, difficulty: {p.get('difficulty', '?')})"
        )
        problem_descriptions.append(desc)

    problems_text = "\n".join(problem_descriptions)

    return f"""You are a DSA interview prep expert. For each of the following LeetCode problems,
generate a concise learning insight. Focus on pattern recognition skills.

Problems:
{problems_text}

Return a JSON object with the following schema:
{INSIGHT_SCHEMA}

Important:
- Generate one insight object per problem listed above
- The "slug" field MUST exactly match the slug provided for each problem
- pattern_hint should explain what words/structure in the problem statement signal the pattern
- key_insight should be the "aha moment" — the core idea needed to solve it
- template_deviation should explain how this specific problem differs from the standard template
- Return ONLY valid JSON, no markdown fences or extra text"""


def generate_batch(
    analyzer,
    problems: List[dict],
    batch_num: int,
    total_batches: int,
    max_retries: int = 3,
) -> List[Dict[str, Any]]:
    """Generate insights for a batch of problems."""

    prompt = build_batch_prompt(problems)
    slugs = {p["slug"] for p in problems}

    for attempt in range(max_retries):
        try:
            response = analyzer.analyze(
                content=prompt,
                prompt="You are a DSA expert and a good teacher who recognize patterns in things and can explain them well. Return only valid JSON.",
            )

            if not response.success:
                logger.warning(f"  Batch {batch_num} attempt {attempt + 1} failed: {response.error}")
                time.sleep(2 ** attempt)
                continue

            # Parse JSON
            text = response.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text[:-3]
                elif "```" in text:
                    text = text[:text.rfind("```")]
            text = text.strip()

            data = json.loads(text)

            # Handle both {insights: [...]} and direct [...] formats
            insights = data.get("insights", data) if isinstance(data, dict) else data
            if not isinstance(insights, list):
                logger.warning(f"  Batch {batch_num} unexpected format, retrying...")
                time.sleep(2 ** attempt)
                continue

            # Validate: ensure we got insights for the expected slugs
            returned_slugs = {i.get("slug") for i in insights}
            missing = slugs - returned_slugs
            if missing:
                logger.warning(f"  Batch {batch_num}: missing insights for {len(missing)} problems")

            logger.info(f"  ✓ Batch {batch_num}/{total_batches}: "
                       f"{len(insights)} insights (tokens: {response.tokens_used})")
            return insights

        except json.JSONDecodeError as e:
            logger.warning(f"  Batch {batch_num} attempt {attempt + 1} JSON error: {e}")
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.warning(f"  Batch {batch_num} attempt {attempt + 1} error: {e}")
            time.sleep(2 ** attempt)

    # Return empty insights for failed batch
    logger.error(f"  ✗ Batch {batch_num} failed after {max_retries} attempts")
    return [
        {
            "slug": p["slug"],
            "pattern_hint": "",
            "key_insight": "",
            "template_deviation": "",
            "common_mistake": "",
            "time_complexity": "",
            "space_complexity": "",
            "_generation_failed": True,
        }
        for p in problems
    ]


def run():
    """Main entry point."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Load enriched problems
    enriched_path = DATA_DIR / "enriched_problems.json"
    if not enriched_path.exists():
        logger.error(f"{enriched_path} not found — run fetch_leetcode.py first")
        return

    enriched = json.loads(enriched_path.read_text())
    logger.info(f"Loaded {len(enriched)} enriched problems")

    # Load existing insights (for resume support)
    output_path = DATA_DIR / "problem_insights.json"
    existing_insights = {}
    if output_path.exists():
        for ins in json.loads(output_path.read_text()):
            if not ins.get("_generation_failed") and ins.get("key_insight"):
                existing_insights[ins["slug"]] = ins
        logger.info(f"Resuming: {len(existing_insights)} insights already generated")

    # Filter out already-generated problems
    remaining = [p for p in enriched if p["slug"] not in existing_insights]
    logger.info(f"Remaining: {len(remaining)} problems to process")

    if not remaining:
        logger.info("All insights already generated!")
        return

    # Initialize AI — use Groq 70b for this task (Gemini free credits limited)
    analyzer = AIAnalyzerFactory.create(AIProvider.GROQ, model="smart")
    logger.info(f"Using AI provider: {analyzer.provider.value} ({analyzer.model_name})")

    # Create batches
    batches = [remaining[i:i + BATCH_SIZE] for i in range(0, len(remaining), BATCH_SIZE)]
    total_batches = len(batches)
    logger.info(f"Processing {len(remaining)} problems in {total_batches} batches of {BATCH_SIZE}")

    all_insights = list(existing_insights.values())

    for batch_num, batch in enumerate(batches, 1):
        logger.info(f"[{batch_num}/{total_batches}] Processing batch: "
                   f"{', '.join(p['slug'][:20] for p in batch[:3])}...")

        insights = generate_batch(analyzer, batch, batch_num, total_batches)
        all_insights.extend(insights)

        # Save after each batch for resume
        with open(output_path, "w") as f:
            json.dump(all_insights, f, indent=2)

        # Delay between batches
        if batch_num < total_batches:
            logger.info(f"  Waiting {BATCH_DELAY}s for TPM cooldown...")
            time.sleep(BATCH_DELAY)

    # Summary
    total = len(all_insights)
    failed = sum(1 for i in all_insights if i.get("_generation_failed"))
    logger.info(f"\nDone! {total} insights total, {total - failed} successful, {failed} failed")
    logger.info(f"Saved to {output_path}")


if __name__ == "__main__":
    run()
