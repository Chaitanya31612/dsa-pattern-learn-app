"""
Generate per-problem solution breakdowns for in-app learning.

Output:
- data/solution_breakdowns.json

Uses Groq AI via batch processing to generate deeply involved
AI solution breakdowns for every problem.
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ai import AIAnalyzerFactory, AIProvider

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"

BATCH_SIZE = 6
BATCH_DELAY = 10  # Seconds between batches to respect 10 RPM limit

SCHEMA = """{
  "breakdowns": [
    {
      "slug": "string - must exactly match the problem slug",
      "intuition": "string - 2 to 3 sentences explaining the intuition connecting the problem constraints to the optimal solution",
      "pattern_connection": "string - 1 to 2 sentences connecting this problem to the underlying pattern or sub-pattern",
      "steps": [
        {
          "title": "string - short title for the step",
          "detail": "string - 1 sentence explaining the details of the step"
        }
      ],
      "java_pseudocode": "string - concise, comment-annotated Java code skeleton/template for this specific problem",
      "edge_cases": ["list of 3 to 6 edge cases to consider"],
      "alternatives": [
        {
          "approach": "string - name of alternative approach (e.g., Brute Force)",
          "tradeoff": "string - 1 sentence explaining why this alternative is worse or better"
        }
      ]
    }
  ]
}"""

def build_batch_prompt(problems: List[dict], insights_by_slug: Dict[str, dict], patterns_by_id: Dict[str, dict]) -> str:
    problems_text = ""
    for p in problems:
        slug = p.get('slug', '')
        insight = insights_by_slug.get(slug, {})
        pattern_id = p.get('pattern_id', p.get('pattern', '').lower().replace(' ', '-'))
        pattern_context = patterns_by_id.get(pattern_id, {})

        problems_text += f"---\n"
        problems_text += f"Problem: {p.get('title', '')} (slug: {slug}) | Difficulty: {p.get('difficulty', '')}\n"
        problems_text += f"Pattern: {p.get('pattern', '')}\n"
        problems_text += f"Pattern hint: {insight.get('pattern_hint', '')}\n"
        problems_text += f"Key insight: {insight.get('key_insight', '')}\n"

        # Inject user feedback for Monotonic Stack span calculation
        pattern_name = p.get('pattern', '')
        if pattern_name == 'Stack' and 'monotonic' in insight.get('key_insight', '').lower():
            problems_text += "Special Instruction for this problem: For monotonic stacks, clearly explain calculating the 'span' as the difference between the current index and the popped index, plus 1 (e.g. current_index - stack_top_index + 1). Use this approach rather than a brute-force span search.\n"

        problems_text += f"Common mistake: {insight.get('common_mistake', '')}\n\n"

    return f"""You are an expert DSA coding interview tutor. Generate extremely high-quality, step-by-step solution breakdowns for the following LeetCode problems.

Problems:
{problems_text}

Return ONLY a single valid JSON object adhering exactly to this schema:
{SCHEMA}

Important Instructions:
- "slug" must exactly match the slug provided for each problem.
- Generate EXACTLY one breakdown per problem in the batch.
- "steps" should have 4 to 6 logical steps for the optimal solution.
- "java_pseudocode" must be syntactically valid Java class methods representing a strong skeleton.
- "alternatives" should list 1 to 3 alternate approaches and their tradeoffs.
- Output raw JSON only.
"""

def generate_batch(
    analyzer,
    batch: List[dict],
    insights_by_slug: Dict[str, dict],
    patterns_by_id: Dict[str, dict],
    batch_num: int,
    total_batches: int,
    max_retries: int = 3
) -> List[Dict[str, Any]]:

    prompt = build_batch_prompt(batch, insights_by_slug, patterns_by_id)
    slugs = {p["slug"] for p in batch if "slug" in p}

    for attempt in range(max_retries):
        try:
            response = analyzer.analyze(
                content=prompt,
                prompt="You are an expert DSA tutor. Output raw valid JSON only.",
                json_mode=True
            )

            if not response.success:
                logger.warning(f"  Batch {batch_num} attempt {attempt + 1} failed: {response.error}")
                time.sleep(2 ** attempt)
                continue

            text = response.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text[:-3]
                elif "```" in text:
                    text = text[:text.rfind("```")]
            text = text.strip()

            data = json.loads(text, strict=False)

            breakdowns = data.get("breakdowns", data) if isinstance(data, dict) else data

            if not isinstance(breakdowns, list):
                logger.warning(f"  Batch {batch_num} unexpected format (not list), retrying...")
                time.sleep(2 ** attempt)
                continue

            returned_slugs = {b.get("slug") for b in breakdowns if isinstance(b, dict)}
            missing = slugs - returned_slugs
            if missing:
                logger.warning(f"  Batch {batch_num}: missing breakdowns for {missing}")

            logger.info(f"  ✓ Batch {batch_num}/{total_batches}: {len(breakdowns)} breakdowns generated.")
            return breakdowns

        except json.JSONDecodeError as e:
            logger.warning(f"  Batch {batch_num} attempt {attempt + 1} JSON parse error: {e}")
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.warning(f"  Batch {batch_num} attempt {attempt + 1} error: {e}")
            time.sleep(2 ** attempt)

    logger.error(f"  ✗ Batch {batch_num} failed after {max_retries} attempts.")
    return []

def run(force_restart: bool = False):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    enriched_path = DATA_DIR / "enriched_problems.json"
    patterns_path = DATA_DIR / "patterns.json"
    insights_path = DATA_DIR / "problem_insights.json"

    if not enriched_path.exists() or not patterns_path.exists() or not insights_path.exists():
        logger.error("Missing required files (enriched_problems.json, patterns.json, problem_insights.json)")
        return

    enriched = json.loads(enriched_path.read_text())
    patterns = json.loads(patterns_path.read_text())
    insights = json.loads(insights_path.read_text())

    insights_by_slug = {i.get("slug"): i for i in insights if isinstance(i, dict) and "slug" in i}
    patterns_by_id = {p.get("sub_pattern_id", p.get("pattern_id")): p for p in patterns if isinstance(p, dict)}

    out_path = DATA_DIR / "solution_breakdowns.json"
    existing_data = {}
    if out_path.exists() and not force_restart:
        try:
            old_output = json.loads(out_path.read_text())
            if "problems" in old_output:
                existing_data = old_output["problems"]
            elif isinstance(old_output, dict):
                existing_data = old_output
        except json.JSONDecodeError:
            pass

    # For existing deterministic solutions from previous version, we might want to filter them out
    # to enforce only AI generated solutions if they lack "source": "ai", but we'll trust user ran it cleanly
    # or let them manually delete solution_breakdowns.json if they want a clean rerun.
    ai_existing_data = {k: v for k, v in existing_data.items() if v.get("source") == "ai"}
    if len(ai_existing_data) != len(existing_data):
         logger.info(f"Filtered out {len(existing_data) - len(ai_existing_data)} old deterministic breakdowns")
         existing_data = ai_existing_data

    logger.info(f"Resuming with {len(existing_data)} existing AI breakdowns.")

    remaining = [p for p in enriched if p.get("slug") and p["slug"] not in existing_data and p.get("score", 0) > 0]

    # Sort remaining by score descending to prioritize highly asked
    remaining = sorted(remaining, key=lambda p: float(p.get("score", 0)), reverse=True)

    if not remaining:
        logger.info("All solution breakdowns already generated!")
        return

    analyzer = AIAnalyzerFactory.create(AIProvider.GEMINI, model="flash")
    logger.info(f"Using AI provider: {analyzer.provider.value} ({analyzer.model_name})")

    batches = [remaining[i:i+BATCH_SIZE] for i in range(0, len(remaining), BATCH_SIZE)]
    total_batches = len(batches)

    logger.info(f"Processing {len(remaining)} remaining problems in {total_batches} batches...")

    results = dict(existing_data)
    ai_enriched_count = len(existing_data)

    for batch_num, batch in enumerate(batches, 1):
        logger.info(f"[{batch_num}/{total_batches}] Batch: {', '.join(p['slug'] for p in batch)}...")

        breakdowns = generate_batch(analyzer, batch, insights_by_slug, patterns_by_id, batch_num, total_batches)

        for b in breakdowns:
            if not isinstance(b, dict): continue
            slug = b.get("slug")
            if not slug: continue

            b["source"] = "ai"
            results[slug] = b
            ai_enriched_count += 1

        output = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "meta": {
                "total_problems": len(results),
                "ai_enriched": True,
                "ai_provider": analyzer.provider.value,
                "ai_model": analyzer.model_name,
                "ai_enriched_count": ai_enriched_count,
            },
            "problems": results,
        }
        out_path.write_text(json.dumps(output, indent=2))

        if batch_num < total_batches:
            time.sleep(BATCH_DELAY)

    logger.info(f"\\nDone! Saved {len(results)} solution breakdowns to {out_path}")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate AI batched solution breakdowns")
    parser.add_argument("--force-restart", action="store_true", help="Ignore existing data and restart from scratch")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    run(force_restart=args.force_restart)
