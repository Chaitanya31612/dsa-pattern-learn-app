"""
Parse Striver's SDE Sheet to extract problems.

Striver's SDE sheet is at takeuforward.org. Since it's JS-rendered,
we use crawl4ai's AsyncWebCrawler (headless browser) to fetch the
fully-rendered HTML, then extract problems from the embedded JSON data.
Falls back to a curated static seed if crawl4ai fails.
"""

import asyncio
import json
import re
import logging
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"

# Striver's SDE Sheet — focused, top interview problems
STRIVER_SHEET_URL = "https://takeuforward.org/dsa/strivers-sde-sheet-top-coding-interview-problems"

# Mapping of Striver sections → our pattern names (for later merging)
SECTION_TO_PATTERN = {
    "arrays": "Arrays & Hashing",
    "sorting": "Arrays & Hashing",
    "binary search": "Binary Search",
    "strings": "Arrays & Hashing",
    "linked list": "Linked List",
    "recursion": "Backtracking",
    "bit manipulation": "Bit Manipulation",
    "stack": "Stack",
    "queue": "Stack",
    "sliding window": "Sliding Window",
    "two pointer": "Two Pointers",
    "heap": "Heap / Priority Queue",
    "greedy": "Greedy",
    "binary tree": "Trees",
    "binary search tree": "Trees",
    "graph": "Graphs",
    "dynamic programming": "DP",
    "trie": "Tries",
}


async def crawl_striver() -> Optional[str]:
    """
    Use crawl4ai AsyncWebCrawler to fetch the JS-rendered Striver page.
    Returns the HTML string or None on failure.
    """
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

        logger.info("Crawling Striver SDE sheet with crawl4ai...")

        browser_config = BrowserConfig(
            headless=True,
            java_script_enabled=True,
        )
        crawler_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_until="networkidle",
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(
                url=STRIVER_SHEET_URL,
                config=crawler_config,
            )

            if result.success:
                logger.info(f"crawl4ai success, HTML length: {len(result.html)}")
                return result.html
            else:
                logger.warning(f"crawl4ai returned failure: {result.error_message}")
                return None

    except Exception as e:
        logger.warning(f"crawl4ai failed: {e}")
        return None


def parse_embedded_json(html: str) -> list[dict]:
    """
    Extract problems from the JSON data embedded in the page HTML.

    The takeuforward.org page (Next.js) embeds problem data inside
    <script>self.__next_f.push(...)</script> tags with backslash-escaped
    quotes. The structure is:
      \"sections\":[{\"category_name\":\"Arrays\",\"problems\":[
        {\"problem_name\":\"...\",\"leetcode\":\"...\", ...}, ...
      ]}, ...]
    """
    # The HTML contains escaped JSON inside Next.js script payloads.
    # Unescape backslash-quoted strings so we can parse them.
    unescaped = html.replace('\\"', '"')

    problems = []
    lc_re = re.compile(r"https?://leetcode\.com/problems/([^/?\"\\]+)")

    # Extract the sections JSON array
    sections_match = re.search(
        r'"sections"\s*:\s*(\[\{.*?\}\])\s*,\s*"(?:lastUpdated|knowMoreHref|heading)',
        unescaped,
        re.DOTALL,
    )
    if not sections_match:
        # Broader fallback
        sections_match = re.search(r'"sections"\s*:\s*(\[\{.+?\}\])', unescaped, re.DOTALL)

    if not sections_match:
        logger.warning("Could not find sections JSON in HTML, using regex fallback")
        return _parse_problems_regex(unescaped)

    try:
        sections_str = sections_match.group(1)
        # Handle Next.js $undefined placeholders
        sections_str = sections_str.replace('"$undefined"', 'null')
        sections_str = re.sub(r':\$undefined', ':null', sections_str)
        sections = json.loads(sections_str)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse sections JSON: {e}, using regex fallback")
        return _parse_problems_regex(unescaped)

    seen_slugs: set[str] = set()

    for section in sections:
        category = section.get("category_name", "Unknown")

        for prob in section.get("problems", []):
            lc_url = prob.get("leetcode", "")
            if not lc_url:
                continue

            match = lc_re.search(lc_url)
            if not match:
                continue

            slug = match.group(1)
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            title = prob.get("problem_name", slug.replace("-", " ").title())

            problems.append({
                "slug": slug,
                "title": title,
                "leetcode_url": f"https://leetcode.com/problems/{slug}/",
                "section": category,
                "difficulty": prob.get("difficulty", "Unknown"),
                "source": "striver",
            })

    return problems


def _parse_problems_regex(html: str) -> list[dict]:
    """
    Fallback: extract problems directly via regex when JSON parsing fails.
    Finds all problem_name + leetcode URL pairs in the raw HTML.
    """
    problems = []
    seen_slugs: set[str] = set()
    lc_re = re.compile(r"https?://leetcode\.com/problems/([^/?\"\\]+)")

    # Find all problem blocks: "problem_name":"...","article":"...","youtube":"...","leetcode":"..."
    pattern = re.compile(
        r'"problem_name"\s*:\s*"([^"]+)".*?"leetcode"\s*:\s*"(https?://leetcode\.com/problems/[^"]+)"',
        re.DOTALL,
    )

    for match in pattern.finditer(html):
        title = match.group(1)
        lc_url = match.group(2)

        slug_match = lc_re.search(lc_url)
        if not slug_match:
            continue

        slug = slug_match.group(1)
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        problems.append({
            "slug": slug,
            "title": title,
            "leetcode_url": f"https://leetcode.com/problems/{slug}/",
            "section": "Unknown",
            "source": "striver",
        })

    return problems


def get_static_seed() -> list[dict]:
    """
    Fallback static seed of Striver's key problems.
    These are the most commonly cited problems from Striver's SDE sheet.
    """
    seed = [
        # Arrays
        {"slug": "set-matrix-zeroes", "title": "Set Matrix Zeroes", "section": "Arrays"},
        {"slug": "pascals-triangle", "title": "Pascal's Triangle", "section": "Arrays"},
        {"slug": "next-permutation", "title": "Next Permutation", "section": "Arrays"},
        {"slug": "sort-colors", "title": "Sort Colors", "section": "Arrays"},
        {"slug": "majority-element", "title": "Majority Element", "section": "Arrays"},
        {"slug": "majority-element-ii", "title": "Majority Element II", "section": "Arrays"},
        {"slug": "unique-paths", "title": "Unique Paths", "section": "Arrays"},
        {"slug": "reverse-pairs", "title": "Reverse Pairs", "section": "Arrays"},
        {"slug": "pow-x-n", "title": "Pow(x, n)", "section": "Arrays"},

        # Linked List
        {"slug": "rotate-list", "title": "Rotate List", "section": "Linked List"},
        {"slug": "copy-list-with-random-pointer", "title": "Copy List with Random Pointer", "section": "Linked List"},
        {"slug": "flatten-a-multilevel-doubly-linked-list", "title": "Flatten a Multilevel Doubly Linked List", "section": "Linked List"},

        # Greedy
        {"slug": "assign-cookies", "title": "Assign Cookies", "section": "Greedy"},
        {"slug": "lemonade-change", "title": "Lemonade Change", "section": "Greedy"},
        {"slug": "jump-game-ii", "title": "Jump Game II", "section": "Greedy"},
        {"slug": "candy", "title": "Candy", "section": "Greedy"},
        {"slug": "non-overlapping-intervals", "title": "Non-overlapping Intervals", "section": "Greedy"},

        # Binary Search
        {"slug": "search-in-rotated-sorted-array-ii", "title": "Search in Rotated Sorted Array II", "section": "Binary Search"},
        {"slug": "find-the-smallest-divisor-given-a-threshold", "title": "Find the Smallest Divisor Given a Threshold", "section": "Binary Search"},
        {"slug": "capacity-to-ship-packages-within-d-days", "title": "Capacity To Ship Packages Within D Days", "section": "Binary Search"},
        {"slug": "split-array-largest-sum", "title": "Split Array Largest Sum", "section": "Binary Search"},

        # Strings
        {"slug": "repeated-string-match", "title": "Repeated String Match", "section": "Strings"},
        {"slug": "count-and-say", "title": "Count and Say", "section": "Strings"},
        {"slug": "compare-version-numbers", "title": "Compare Version Numbers", "section": "Strings"},
        {"slug": "minimum-add-to-make-parentheses-valid", "title": "Minimum Add to Make Parentheses Valid", "section": "Strings"},

        # Stack/Queue
        {"slug": "next-greater-element-ii", "title": "Next Greater Element II", "section": "Stack & Queue"},
        {"slug": "largest-rectangle-in-histogram", "title": "Largest Rectangle in Histogram", "section": "Stack & Queue"},
        {"slug": "sliding-window-maximum", "title": "Sliding Window Maximum", "section": "Stack & Queue"},
        {"slug": "lru-cache", "title": "LRU Cache", "section": "Stack & Queue"},
        {"slug": "lfu-cache", "title": "LFU Cache", "section": "Stack & Queue"},
        {"slug": "online-stock-span", "title": "Online Stock Span", "section": "Stack & Queue"},

        # Trees
        {"slug": "flatten-binary-tree-to-linked-list", "title": "Flatten Binary Tree to Linked List", "section": "Binary Trees"},
        {"slug": "construct-binary-tree-from-preorder-and-inorder-traversal", "title": "Construct Binary Tree from Preorder and Inorder Traversal", "section": "Binary Trees"},
        {"slug": "serialize-and-deserialize-binary-tree", "title": "Serialize and Deserialize Binary Tree", "section": "Binary Trees"},
        {"slug": "count-complete-tree-nodes", "title": "Count Complete Tree Nodes", "section": "Binary Trees"},

        # Graphs
        {"slug": "number-of-provinces", "title": "Number of Provinces", "section": "Graphs"},
        {"slug": "rotting-oranges", "title": "Rotting Oranges", "section": "Graphs"},
        {"slug": "surrounded-regions", "title": "Surrounded Regions", "section": "Graphs"},
        {"slug": "number-of-enclaves", "title": "Number of Enclaves", "section": "Graphs"},
        {"slug": "word-ladder", "title": "Word Ladder", "section": "Graphs"},
        {"slug": "cheapest-flights-within-k-stops", "title": "Cheapest Flights Within K Stops", "section": "Graphs"},
        {"slug": "network-delay-time", "title": "Network Delay Time", "section": "Graphs"},

        # DP
        {"slug": "matrix-chain-multiplication", "title": "Matrix Chain Multiplication", "section": "Dynamic Programming"},
        {"slug": "edit-distance", "title": "Edit Distance", "section": "Dynamic Programming"},
        {"slug": "distinct-subsequences", "title": "Distinct Subsequences", "section": "Dynamic Programming"},
        {"slug": "palindrome-partitioning", "title": "Palindrome Partitioning", "section": "Dynamic Programming"},
        {"slug": "word-break", "title": "Word Break", "section": "Dynamic Programming"},
        {"slug": "minimum-cost-to-cut-a-stick", "title": "Minimum Cost to Cut a Stick", "section": "Dynamic Programming"},
        {"slug": "burst-balloons", "title": "Burst Balloons", "section": "Dynamic Programming"},
        {"slug": "partition-equal-subset-sum", "title": "Partition Equal Subset Sum", "section": "Dynamic Programming"},
    ]

    for p in seed:
        p["leetcode_url"] = f"https://leetcode.com/problems/{p['slug']}/"
        p["difficulty"] = "Unknown"
        p["source"] = "striver"

    return seed


async def async_run():
    """Async main entry point."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    problems: list[dict] = []

    # Try crawl4ai (async)
    html = await crawl_striver()
    if html:
        problems = parse_embedded_json(html)
        logger.info(f"crawl4ai extracted {len(problems)} problems")

    # Fallback to static seed if scraping yielded too few results
    if len(problems) < 20:
        logger.info("Scraping yielded too few results, using static seed")
        problems = get_static_seed()
        logger.info(f"Static seed: {len(problems)} problems")

    # Deduplicate by slug
    seen: set[str] = set()
    unique_problems: list[dict] = []
    for p in problems:
        if p["slug"] not in seen:
            seen.add(p["slug"])
            unique_problems.append(p)
    problems = unique_problems

    # Summary
    sections: dict[str, int] = {}
    for p in problems:
        s = p.get("section", "Unknown")
        sections[s] = sections.get(s, 0) + 1

    logger.info(f"\nTotal: {len(problems)} unique problems across {len(sections)} sections:")
    for section, count in sorted(sections.items(), key=lambda x: -x[1]):
        logger.info(f"  {section}: {count}")

    # Save
    output_path = DATA_DIR / "striver_raw.json"
    with open(output_path, "w") as f:
        json.dump(problems, f, indent=2)
    logger.info(f"\nSaved to {output_path}")

    return problems


def run():
    """Sync wrapper for the async entry point."""
    return asyncio.run(async_run())


if __name__ == "__main__":
    run()
