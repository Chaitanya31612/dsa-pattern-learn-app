"""
Generate detailed learning content for each AI-deduced sub-pattern.

Reads `data/dynamic_sub_patterns.json` and uses Groq to generate deep learning
resource content (explanation, mental model, Java template, trigger phrases) for each one.
Uses batched requests to respect API rate limits.
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

BATCH_SIZE = 5
BATCH_DELAY = 20 # seconds

SCHEMA = """{
  "pattern_id": "string - kebab-case parent pattern ID",
  "sub_pattern_id": "string - kebab-case sub pattern ID",
  "name": "string - human readable sub pattern name",
  "explanation": "string - detailed pedagogical explanation of this sub-pattern",
  "mental_model": "string - concise, powerful mental model to remember this approach",
  "template_code_java": "string - the core Java code template that solves these types of problems cleanly. Use class Solution { ... }",
  "trigger_phrases": ["list of 3 to 6 words/phrases indicating this sub-pattern is required"]
}"""

def build_batch_prompt(sub_patterns: List[Dict[str, Any]], parent_pattern_name: str, parent_pattern_id: str) -> str:
    sub_patterns_text = "\\n\\n".join(
        f"--- Sub-Pattern: {sp['name']} (ID: {sp['sub_pattern_id']}) ---\\n"
        f"Description: {sp['description']}\\n"
        f"Problems assigned to this: {', '.join(sp.get('problem_slugs', []))}"
        for sp in sub_patterns
    )

    return f"""You are an elite Data Structures & Algorithms Professor.
I need you to generate deep, highly specific learning content for several 'Sub-Patterns'
belonging to the parent pattern: "{parent_pattern_name}".

For each sub-pattern listed below, generate the details according to the schema.
Return a single JSON object with a "sub_patterns" key containing the array of results.

Sub-Patterns Context:
{sub_patterns_text}

JSON Schema for EACH item in the "sub_patterns" array:
{SCHEMA}

Important Instructions:
- "pattern_id" must be EXACTLY "{parent_pattern_id}".
- "sub_pattern_id" and "name" must EXACTLY match the input values I provided above.
- Ensure the "template_code_java" is accurate, well-commented, and truly representative of the unique sub-pattern mechanics. Only Java code is required.
- CRITICAL: The entire output must be VALID JSON. Any double quotes inside string values (especially in "template_code_java") MUST be escaped with a backslash (e.g., \\").
- Return ONLY the JSON object, no markdown blocks or extra text.
"""

def generate_batch(
    analyzer,
    sub_patterns: List[Dict[str, Any]],
    parent_pattern_name: str,
    parent_pattern_id: str,
    batch_num: int,
    total_batches: int,
    max_retries: int = 3
) -> List[Dict[str, Any]]:

    prompt = build_batch_prompt(sub_patterns, parent_pattern_name, parent_pattern_id)

    for attempt in range(max_retries):
        try:
            # Use json_mode if available (supported by Groq)
            response = analyzer.analyze(
                content=prompt,
                prompt="You are an expert DSA professor. Return ONLY a valid JSON object with a 'sub_patterns' key.",
                json_mode=True
            )

            if not response.success:
                logger.warning(f"  Batch {batch_num} attempt {attempt + 1} failed: {response.error}")
                time.sleep(2 ** attempt)
                continue

            text = response.content.strip()
            # Handle potential markdown fencing if not using JSON mode
            if text.startswith("```"):
                text = text.split("\\n", 1)[1]
                if text.endswith("```"):
                    text = text[:-3]
                elif "```" in text:
                    text = text[:text.rfind("```")]
            text = text.strip()

            data = json.loads(text, strict=False)

            # Support both array and object wrapping
            if isinstance(data, dict) and "sub_patterns" in data:
                data = data["sub_patterns"]

            if not isinstance(data, list):
                logger.warning(f"  Batch {batch_num} unexpected format (not list), retrying...")
                time.sleep(2 ** attempt)
                continue

            logger.info(f"  ✓ Batch {batch_num}/{total_batches}: {len(data)} sub-pattern details generated.")
            return data

        except json.JSONDecodeError as e:
            logger.warning(f"  Batch {batch_num} attempt {attempt + 1} JSON parse error: {e}")
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.warning(f"  Batch {batch_num} attempt {attempt + 1} error: {e}")
            time.sleep(2 ** attempt)

    logger.error(f"  ✗ Batch {batch_num} failed after {max_retries} attempts.")
    return []

def run():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    input_path = DATA_DIR / "dynamic_sub_patterns.json"
    if not input_path.exists():
        logger.error(f"{input_path} missing. Run generate_dynamic_sub_patterns.py first.")
        return

    sub_patterns_data = json.loads(input_path.read_text())

    PATTERNS_MAP = {
        "arrays-hashing": "Arrays & Hashing",
        "two-pointers": "Two Pointers",
        "sliding-window": "Sliding Window",
        "stack": "Stack",
        "binary-search": "Binary Search",
        "linked-list": "Linked List",
        "trees": "Trees",
        "tries": "Tries",
        "heap-priority-queue": "Heap / Priority Queue",
        "backtracking": "Backtracking",
        "graphs": "Graphs",
        "1d-dp": "1-D DP",
        "2d-dp": "2-D DP",
        "greedy": "Greedy",
        "intervals": "Intervals",
        "bit-manipulation": "Bit Manipulation",
        "math-geometry": "Math & Geometry"
    }

    # Flatten the inputs to generate flat list of sub-patterns
    all_sub_patterns = []
    for pattern_id, items in sub_patterns_data.items():
        if not items: continue
        pattern_name = PATTERNS_MAP.get(pattern_id, pattern_id)
        for sp in items:
            sp["_parent_pattern_id"] = pattern_id
            sp["_parent_pattern_name"] = pattern_name
            all_sub_patterns.append(sp)

    if not all_sub_patterns:
        logger.warning("No sub-patterns found in dynamic_sub_patterns.json")
        return

    out_path = DATA_DIR / "patterns.json"
    existing_items = []
    existing_ids = set()
    if out_path.exists():
        existing_items = json.loads(out_path.read_text())
        existing_ids = {p.get("sub_pattern_id") for p in existing_items if p.get("explanation")}
        logger.info(f"Resuming with {len(existing_ids)} sub-patterns already generated.")

    remaining = [sp for sp in all_sub_patterns if sp["sub_pattern_id"] not in existing_ids]

    if not remaining:
        logger.info("All sub-pattern details already generated!")
        return

    analyzer = AIAnalyzerFactory.create(AIProvider.GROQ, model="smart")
    logger.info(f"Using: {analyzer.provider.value} ({analyzer.model_name})")

    # Group by parent pattern to batch intelligently
    grouped_remaining = {}
    for sp in remaining:
        pid = sp["_parent_pattern_id"]
        if pid not in grouped_remaining:
            grouped_remaining[pid] = []
        grouped_remaining[pid].append(sp)

    results = list(existing_items)

    total_ops = len(grouped_remaining)
    current_op = 0

    for pid, sp_list in grouped_remaining.items():
        current_op += 1
        p_name = sp_list[0]["_parent_pattern_name"]

        batches = [sp_list[i:i + BATCH_SIZE] for i in range(0, len(sp_list), BATCH_SIZE)]
        total_batches = len(batches)

        logger.info(f"[{current_op}/{total_ops}] Processing {len(sp_list)} sub-patterns for {p_name} across {total_batches} batches...")

        for batch_num, batch in enumerate(batches, 1):
            generated_data = generate_batch(analyzer, batch, p_name, pid, batch_num, total_batches)

            # Enrich original data structure
            for raw_sp, gen_sp in zip(batch, generated_data):
                ans = {
                    "pattern_id": pid,
                    "sub_pattern_id": raw_sp["sub_pattern_id"],
                    "name": raw_sp["name"],
                    "description": raw_sp["description"],
                    "problem_slugs": raw_sp.get("problem_slugs", []),
                    "explanation": gen_sp.get("explanation", ""),
                    "mental_model": gen_sp.get("mental_model", ""),
                    "template_code_java": gen_sp.get("template_code_java", ""),
                    "trigger_phrases": gen_sp.get("trigger_phrases", [])
                }
                results.append(ans)

            # Dump
            with open(out_path, "w") as f:
                json.dump(results, f, indent=2)

            if batch_num < total_batches or current_op < total_ops:
                time.sleep(BATCH_DELAY)

    logger.info(f"\\nDone! Saved {len(results)} enriched sub-patterns to {out_path}")

if __name__ == "__main__":
    run()
