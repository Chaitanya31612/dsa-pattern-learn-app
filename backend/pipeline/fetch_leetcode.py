"""
Fetch metadata for curated problems from LeetCode.

For each curated problem, fetches:
- difficulty (Easy/Medium/Hard)
- acceptance_rate
- topic_tags (list of tag names)
- description (HTML)

Uses LeetCode's bulk stats endpoint as a fallback when GraphQL is blocked.
Rate limited to ~1 req/sec with exponential backoff.
Supports resuming from partial runs (skips already-fetched problems).
"""

import json
import time
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
LEETCODE_PROBLEMS_ALL_URL = "https://leetcode.com/api/problems/all/"

QUESTION_QUERY = """
query getQuestion($titleSlug: String!) {
    question(titleSlug: $titleSlug) {
        questionId
        title
        titleSlug
        difficulty
        content
        topicTags {
            name
            slug
        }
        stats
        acRate
    }
}
"""

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
DIFFICULTY_MAP = {
    1: "Easy",
    2: "Medium",
    3: "Hard",
}


def init_session() -> requests.Session:
    """
    Initialize a requests session with proper LeetCode cookies and CSRF token.
    LeetCode requires a csrftoken cookie + X-CSRFToken header for GraphQL.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://leetcode.com",
        "Origin": "https://leetcode.com",
    })

    raw_cookie = os.getenv("LEETCODE_COOKIE", "").strip()
    if raw_cookie:
        # Optional manual cookie override from browser for bot-protected networks.
        for chunk in raw_cookie.split(";"):
            if "=" not in chunk:
                continue
            k, v = chunk.split("=", 1)
            session.cookies.set(k.strip(), v.strip(), domain=".leetcode.com")
        logger.info("Loaded cookies from LEETCODE_COOKIE")

    # Visit leetcode.com to get cookies (especially csrftoken)
    logger.info("Initializing session with LeetCode...")
    try:
        resp = session.get("https://leetcode.com/", timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning(f"Failed to init session: {e}")

    # Extract CSRF token from cookies
    csrf_token = session.cookies.get("csrftoken", "")
    if csrf_token:
        session.headers.update({"X-CSRFToken": csrf_token})
        logger.info("CSRF token acquired")
    else:
        logger.warning("No CSRF token found in cookies — requests may fail")

    return session


def fetch_bulk_metadata(session: requests.Session) -> Dict[str, Dict[str, Any]]:
    """
    Fetch metadata snapshot from LeetCode's public problems-all API.
    This endpoint is more stable than GraphQL and returns difficulty + AC stats.
    """
    try:
        resp = session.get(LEETCODE_PROBLEMS_ALL_URL, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch bulk metadata: {e}")
        return {}
    except ValueError as e:
        logger.warning(f"Failed to parse bulk metadata JSON: {e}")
        return {}

    pairs = payload.get("stat_status_pairs", [])
    index: Dict[str, Dict[str, Any]] = {}

    for item in pairs:
        stat = item.get("stat", {})
        slug = stat.get("question__title_slug")
        if not slug:
            continue

        level = item.get("difficulty", {}).get("level")
        difficulty = DIFFICULTY_MAP.get(level)

        total_submitted = stat.get("total_submitted") or 0
        total_acs = stat.get("total_acs") or 0
        ac_rate = round((total_acs * 100.0 / total_submitted), 1) if total_submitted else None

        index[slug] = {
            "leetcode_id": stat.get("frontend_question_id") or stat.get("question_id"),
            "difficulty": difficulty,
            "acceptance_rate": ac_rate,
        }

    logger.info(f"Loaded bulk metadata for {len(index)} slugs")
    return index


def _parse_graphql_question(data: Dict[str, Any], slug: str) -> Optional[Dict[str, Any]]:
    question = data.get("data", {}).get("question")
    if not question:
        logger.warning(f"  No data returned for slug: {slug}")
        return None

    ac_rate = None
    if question.get("acRate") is not None:
        ac_rate = round(float(question["acRate"]), 1)

    return {
        "leetcode_id": question.get("questionId"),
        "difficulty": question.get("difficulty"),
        "acceptance_rate": ac_rate,
        "topic_tags": [t["name"] for t in (question.get("topicTags") or [])],
        "description_html": question.get("content", ""),
    }


def fetch_problem_metadata(slug: str, session: requests.Session) -> tuple[Optional[Dict[str, Any]], Optional[int]]:
    """
    Fetch metadata for a single problem from LeetCode GraphQL API.

    Returns (metadata, status_code).
    """
    payload = {
        "query": QUESTION_QUERY,
        "variables": {"titleSlug": slug},
    }

    try:
        post_resp = session.post(
            LEETCODE_GRAPHQL_URL,
            json=payload,
            timeout=15,
        )

        if post_resp.status_code not in (403, 499):
            post_resp.raise_for_status()
            return _parse_graphql_question(post_resp.json(), slug), post_resp.status_code

        # CSRF/bot filters can block POST but still allow GET query params.
        params = {
            "query": QUESTION_QUERY,
            "variables": json.dumps({"titleSlug": slug}),
            "operationName": "getQuestion",
        }
        get_resp = session.get(LEETCODE_GRAPHQL_URL, params=params, timeout=15)
        get_resp.raise_for_status()
        return _parse_graphql_question(get_resp.json(), slug), get_resp.status_code

    except requests.exceptions.RequestException as e:
        logger.warning(f"  Request error for {slug}: {e}")
        status = None
        resp = getattr(e, "response", None)
        if resp is not None:
            status = resp.status_code
            logger.warning(f"  HTTP {status} for {slug}")
        return None, status
    except (KeyError, ValueError, TypeError) as e:
        logger.warning(f"  Parse error for {slug}: {e}")
        return None, None


def run():
    """
    Main entry point. Fetches metadata for all curated problems.
    Supports resume — loads existing enriched data and skips already-fetched slugs.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Load curated problems
    curated_path = DATA_DIR / "curated_problems.json"
    if not curated_path.exists():
        logger.error(f"{curated_path} not found — run merge_and_curate.py first")
        return

    curated = json.loads(curated_path.read_text())
    logger.info(f"Loaded {len(curated)} curated problems")

    # Load existing enriched data (for resume support)
    output_path = DATA_DIR / "enriched_problems.json"
    enriched = {}
    if output_path.exists():
        existing = json.loads(output_path.read_text())
        # Only count problems with actual metadata as already fetched
        for p in existing:
            if p.get("difficulty") is not None:
                enriched[p["slug"]] = p
        logger.info(f"Resuming: {len(enriched)} already fetched, {len(curated) - len(enriched)} remaining")

    session = init_session()
    bulk_metadata = fetch_bulk_metadata(session)

    # Rate limiting config
    base_delay = 1.0   # seconds between requests
    max_retries = 3
    backoff_factor = 2.0
    graphql_enabled = True
    graphql_blocked_count = 0
    graphql_blocked_threshold = 5

    success_count = 0
    fail_count = 0

    for i, problem in enumerate(curated):
        slug = problem["slug"]

        # Skip if already fetched
        if slug in enriched:
            continue

        # Rate limit
        time.sleep(base_delay)

        # Seed with bulk metadata when available; this avoids total failure when GraphQL is blocked.
        metadata = bulk_metadata.get(slug, {}).copy()

        if graphql_enabled:
            for attempt in range(max_retries):
                gql_meta, status_code = fetch_problem_metadata(slug, session)

                if gql_meta is not None:
                    metadata = {**metadata, **gql_meta}
                    graphql_blocked_count = 0
                    break

                if status_code in (403, 499):
                    graphql_blocked_count += 1
                    if graphql_blocked_count >= graphql_blocked_threshold:
                        graphql_enabled = False
                        logger.warning(
                            "GraphQL appears blocked (repeated 403/499). "
                            "Disabling GraphQL and continuing with bulk metadata only."
                        )
                        break

                # Exponential backoff
                wait = base_delay * (backoff_factor ** (attempt + 1))
                logger.warning(f"  Retry {attempt + 1}/{max_retries} for {slug}, waiting {wait:.1f}s")
                time.sleep(wait)

        if "topic_tags" not in metadata:
            metadata["topic_tags"] = []
        if "description_html" not in metadata:
            metadata["description_html"] = ""

        if metadata.get("difficulty") is not None or metadata.get("leetcode_id") is not None:
            # Merge curated data with fetched metadata
            enriched_problem = {**problem, **metadata}
            enriched[slug] = enriched_problem
            success_count += 1

            if success_count % 10 == 0:
                logger.info(f"  Progress: {success_count + len(enriched) - success_count}/{len(curated)} "
                           f"(just fetched {success_count}, {fail_count} failed)")

                # Periodic save for resume support
                _save(enriched, output_path)
        else:
            fail_count += 1
            # Still keep the curated data even without metadata
            enriched[slug] = {**problem, "difficulty": None, "acceptance_rate": None,
                             "topic_tags": [], "description_html": "", "leetcode_id": None}
            logger.warning(f"  Failed to fetch metadata for: {slug} (#{problem.get('number', '?')})")

        # Progress log every 25 problems
        total_done = sum(1 for s in enriched if enriched[s].get("difficulty") is not None)
        if (i + 1) % 25 == 0:
            logger.info(f"Progress: {i + 1}/{len(curated)} processed, {total_done} enriched, {fail_count} failed")

    # Final save
    _save(enriched, output_path)

    # Summary
    total = len(enriched)
    with_metadata = sum(1 for p in enriched.values() if p.get("difficulty") is not None)
    logger.info(f"\nDone! {total} problems total, {with_metadata} with metadata, "
               f"{total - with_metadata} without metadata")

    # Difficulty distribution
    diff_counts = {}
    for p in enriched.values():
        d = p.get("difficulty", "Unknown") or "Unknown"
        diff_counts[d] = diff_counts.get(d, 0) + 1
    logger.info(f"Difficulty distribution: {diff_counts}")


def _save(enriched: Dict[str, dict], output_path: Path):
    """Save enriched problems to JSON."""
    problems_list = list(enriched.values())
    with open(output_path, "w") as f:
        json.dump(problems_list, f, indent=2)
    logger.info(f"  Saved {len(problems_list)} problems to {output_path}")


if __name__ == "__main__":
    run()
