"""
Build company-frequency metadata for curated LeetCode problems.

Outputs:
- data/company_frequency.json

Data strategy:
1) Deterministic local signals (NeetCode/Striver overlap from enriched_problems).
2) External curated interview lists (Sean Prashad / Tech Interview Handbook / Interview Prep Pro) when reachable.
3) External company-wise feeds when reachable.
4) Optional AI enrichment pass (`--ai-enrich`) to infer likely companies/follow-ups.
"""

import argparse
import json
import logging
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
from dotenv import load_dotenv
from urllib.parse import urljoin

# Load .env from backend root
load_dotenv(Path(__file__).parent.parent / ".env")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"

LEETCODE_SLUG_RE = re.compile(r"https?://leetcode\.com/problems/([a-z0-9-]+)/?")
MARKDOWN_HEADING_RE = re.compile(r"^\s*#{1,6}\s+(.+?)\s*$")

CANONICAL_COMPANIES = {
    "google": "Google",
    "amazon": "Amazon",
    "meta": "Meta",
    "facebook": "Meta",
    "microsoft": "Microsoft",
    "apple": "Apple",
    "netflix": "Netflix",
    "uber": "Uber",
    "airbnb": "Airbnb",
    "adobe": "Adobe",
    "linkedin": "LinkedIn",
    "oracle": "Oracle",
    "atlassian": "Atlassian",
    "bloomberg": "Bloomberg",
    "goldman sachs": "Goldman Sachs",
    "jpmorgan": "JPMorgan",
    "tcs": "TCS",
    "walmart": "Walmart",
}

INTERVIEW_LIST_SOURCES = [
    {
        "id": "grind75",
        "url": "https://www.techinterviewhandbook.org/grind75/",
        "format": "html",
    },
    {
        "id": "sean_prashad",
        "url": "https://seanprashad.com/leetcode-patterns/",
        "format": "html",
    },
    {
        "id": "interview_prep_pro",
        "url": "https://interview-prep-pro.vercel.app/",
        "format": "html",
    },
]

COMPANY_SOURCES = [
    {
        "id": "krishnadey_company_csv_repo",
        "api_url": "https://api.github.com/repos/krishnadey30/LeetCode-Questions-CompanyWise/contents?ref=master",
        "format": "github_csv_repo",
    },
    {
        "id": "liquidslr_company_csv_repo",
        "api_url": "https://api.github.com/repos/liquidslr/interview-company-wise-problems/contents?ref=main",
        "format": "github_csv_repo",
    },
]

# Lightweight follow-up hints for common interview chains.
FOLLOW_UP_HINTS = {
    "two-sum": ["3sum", "4sum", "two-sum-ii-input-array-is-sorted"],
    "merge-intervals": ["insert-interval", "non-overlapping-intervals"],
    "binary-search": ["first-bad-version", "search-in-rotated-sorted-array"],
    "number-of-islands": ["max-area-of-island", "number-of-provinces"],
    "top-k-frequent-elements": ["kth-largest-element-in-an-array", "find-median-from-data-stream"],
    "valid-parentheses": ["generate-parentheses", "longest-valid-parentheses"],
    "word-break": ["word-break-ii", "concatenated-words"],
    "best-time-to-buy-and-sell-stock": ["best-time-to-buy-and-sell-stock-ii", "best-time-to-buy-and-sell-stock-with-cooldown"],
}

TIER_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "very_high": 4,
}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def normalize_company_name(raw: str) -> Optional[str]:
    cleaned = raw.strip().lower()
    cleaned = re.sub(r"\(.*?\)", "", cleaned).strip()
    cleaned = cleaned.replace("&", " and ")
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return None
    return CANONICAL_COMPANIES.get(cleaned)


def fetch_text(url: str, timeout_sec: int = 20) -> Optional[str]:
    try:
        resp = requests.get(url, timeout=timeout_sec)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        logger.warning(f"Failed to fetch {url}: {exc}")
        return None


def fetch_json(url: str, timeout_sec: int = 25) -> Optional[Any]:
    try:
        resp = requests.get(url, timeout=timeout_sec)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.warning(f"Failed to fetch JSON {url}: {exc}")
        return None
    except ValueError as exc:
        logger.warning(f"Failed to parse JSON {url}: {exc}")
        return None


def extract_slugs_from_markdown(text: str) -> Set[str]:
    return {match.group(1) for match in LEETCODE_SLUG_RE.finditer(text)}


def extract_slugs_from_html(text: str) -> Set[str]:
    slugs = {match.group(1) for match in LEETCODE_SLUG_RE.finditer(text)}
    for pattern in [
        re.compile(r'"titleSlug"\s*:\s*"([a-z0-9-]+)"'),
        re.compile(r'"slug"\s*:\s*"([a-z0-9-]+)"'),
        re.compile(r'"(?:questionSlug|problemSlug|leetcodeSlug)"\s*:\s*"([a-z0-9-]+)"'),
        re.compile(r'/problems/([a-z0-9-]+)/'),
    ]:
        slugs.update(match.group(1) for match in pattern.finditer(text))
    return slugs


def extract_candidate_asset_urls(page_url: str, html: str) -> List[str]:
    """
    Extract JS/JSON assets from HTML pages (useful for Next.js static payloads).
    """
    assets: Set[str] = set()
    # script src and link href.
    for match in re.finditer(r'(?:src|href)=["\']([^"\']+)["\']', html):
        raw = match.group(1).strip()
        if not raw:
            continue
        lower = raw.lower()
        if any(token in lower for token in (".js", ".json", "_next/static", "/assets/")):
            assets.add(urljoin(page_url, raw))
    return sorted(assets)


def extract_slugs_from_web_app(
    page_url: str,
    html: str,
    request_delay_sec: float,
    max_assets: int = 30,
) -> Set[str]:
    """
    For pages that don't embed links directly, inspect static assets for slugs.
    """
    slugs = extract_slugs_from_html(html)
    if slugs:
        return slugs

    assets = extract_candidate_asset_urls(page_url, html)
    if not assets:
        return slugs

    for asset_url in assets[:max_assets]:
        text = fetch_text(asset_url, timeout_sec=25)
        if not text:
            continue
        slugs.update(extract_slugs_from_html(text))
        time.sleep(max(request_delay_sec * 0.25, 0.02))
    return slugs


def parse_company_markdown(text: str) -> Dict[str, Set[str]]:
    """
    Parse markdown where headings are company names and rows contain LeetCode URLs.
    """
    mapping: Dict[str, Set[str]] = defaultdict(set)
    current_company: Optional[str] = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        heading_match = MARKDOWN_HEADING_RE.match(line)
        if heading_match:
            current_company = normalize_company_name(heading_match.group(1))
            continue

        if not current_company:
            continue

        for slug in extract_slugs_from_markdown(line):
            mapping[slug].add(current_company)

    return mapping


def parse_company_html(text: str) -> Dict[str, Set[str]]:
    """
    Parse HTML pages where company names appear in headings and rows contain LeetCode links.
    """
    mapping: Dict[str, Set[str]] = defaultdict(set)
    current_company: Optional[str] = None

    try:
        from bs4 import BeautifulSoup
    except Exception:
        # Fallback to plain-text heading parser if bs4 is unavailable.
        return parse_company_markdown(text)

    soup = BeautifulSoup(text, "html.parser")
    body = soup.body or soup
    for node in body.descendants:
        name = getattr(node, "name", None)
        if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            current_company = normalize_company_name(node.get_text(" ", strip=True))
        if name == "a":
            href = (node.get("href") or "").strip()
            if not href or not current_company:
                continue
            match = LEETCODE_SLUG_RE.search(href)
            if match:
                mapping[match.group(1)].add(current_company)

    return mapping


def parse_company_from_filename(filename: str) -> Optional[str]:
    base = filename.rsplit(".", 1)[0].lower()
    token = re.split(r"[_-]", base)[0].strip()
    if token in {"all", "list", "company", "companies"}:
        return None
    return normalize_company_name(token)


def parse_company_from_csv_repo(
    api_url: str,
    request_delay_sec: float,
) -> Dict[str, Set[str]]:
    mapping: Dict[str, Set[str]] = defaultdict(set)
    payload = fetch_json(api_url, timeout_sec=30)
    if not isinstance(payload, list):
        return mapping

    csv_entries = [item for item in payload if isinstance(item, dict) and str(item.get("name", "")).endswith(".csv")]
    for entry in csv_entries:
        filename = str(entry.get("name", ""))
        company = parse_company_from_filename(filename)
        if not company:
            continue
        raw_url = str(entry.get("download_url", "")).strip()
        if not raw_url:
            continue
        csv_text = fetch_text(raw_url, timeout_sec=30)
        if not csv_text:
            continue
        for slug in extract_slugs_from_markdown(csv_text):
            mapping[slug].add(company)
        time.sleep(max(request_delay_sec * 0.15, 0.01))

    return mapping


def compute_frequency_tier(
    source_signals: List[str],
    companies: List[str],
    overlap_bonus: float,
) -> str:
    company_count = len(companies)
    signal_count = len(source_signals)
    # `overlap_bonus` captures known high-value overlap from core curated sources.
    boost = 1 if overlap_bonus >= 1 else 0

    if company_count >= 10 or signal_count >= 5:
        return "very_high"
    if company_count >= (7 - boost) or signal_count >= 4:
        return "high"
    if company_count >= (4 - boost) or signal_count >= 3:
        return "medium"
    return "low"


def strip_code_fences(text: str) -> str:
    payload = text.strip()
    if payload.startswith("```"):
        payload = payload.split("\n", 1)[1] if "\n" in payload else payload
        if payload.endswith("```"):
            payload = payload[:-3]
    return payload.strip()


def ai_enrich_problem(
    analyzer,
    problem: dict,
    source_signals: List[str],
    companies: List[str],
    frequency_tier: str,
) -> Dict[str, Any]:
    prompt = (
        "You are an interview preparation expert.\n"
        "Given the problem metadata, infer likely companies and follow-ups.\n"
        "Return ONLY valid JSON with schema:\n"
        "{"
        "\"companies\": [\"Company\"], "
        "\"frequency_tier\": \"low|medium|high|very_high\", "
        "\"follow_ups\": [\"leetcode-slug\"]"
        "}\n"
        "Constraints:\n"
        "- max 6 companies\n"
        "- max 6 follow_ups\n"
        "- use canonical company names"
    )
    content = (
        f"Title: {problem.get('title', '')}\n"
        f"Slug: {problem.get('slug', '')}\n"
        f"Pattern: {problem.get('pattern', '')}\n"
        f"Current source signals: {source_signals}\n"
        f"Current companies: {companies}\n"
        f"Current frequency tier: {frequency_tier}\n"
    )

    response = analyzer.analyze(content=content, prompt=prompt)
    if not response.success or not response.content:
        return {}

    try:
        parsed = json.loads(strip_code_fences(response.content))
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


def run(
    offline: bool = False,
    ai_enrich: bool = False,
    ai_limit: int = 80,
    request_delay_sec: float = 0.4,
):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    enriched_path = DATA_DIR / "enriched_problems.json"
    if not enriched_path.exists():
        logger.error(f"{enriched_path} not found — run fetch_leetcode.py first")
        return

    enriched = json.loads(enriched_path.read_text())
    logger.info(f"Loaded {len(enriched)} enriched problems")

    curated_slugs = {p["slug"] for p in enriched}
    by_slug = {p["slug"]: p for p in enriched}

    source_membership: Dict[str, Set[str]] = defaultdict(set)
    company_map: Dict[str, Set[str]] = defaultdict(set)

    # Local deterministic signals first.
    for p in enriched:
        slug = p["slug"]
        if p.get("in_neetcode"):
            source_membership[slug].add("neetcode")
        if p.get("in_striver"):
            source_membership[slug].add("striver")
        if p.get("in_both"):
            source_membership[slug].add("bridge_overlap")

    fetched_lists: List[str] = []
    fetched_company_sources: List[str] = []

    if not offline:
        logger.info("Fetching external interview lists...")
        for source in INTERVIEW_LIST_SOURCES:
            text = fetch_text(source["url"])
            if not text:
                continue
            if source["format"] == "markdown":
                slugs = extract_slugs_from_markdown(text)
            elif source["format"] == "html":
                slugs = extract_slugs_from_web_app(
                    page_url=source["url"],
                    html=text,
                    request_delay_sec=request_delay_sec,
                )
            else:
                slugs = set()
            hits = slugs & curated_slugs
            for slug in hits:
                source_membership[slug].add(source["id"])
            fetched_lists.append(source["id"])
            logger.info(f"  {source['id']}: matched {len(hits)} curated slugs")
            time.sleep(request_delay_sec)

        logger.info("Fetching external company-wise sources...")
        for source in COMPANY_SOURCES:
            if source["format"] == "company_markdown":
                text = fetch_text(source["url"])
                if not text:
                    continue
                parsed = parse_company_markdown(text)
            elif source["format"] == "company_html":
                text = fetch_text(source["url"])
                if not text:
                    continue
                parsed = parse_company_html(text)
            elif source["format"] == "github_csv_repo":
                parsed = parse_company_from_csv_repo(
                    api_url=source["api_url"],
                    request_delay_sec=request_delay_sec,
                )
            else:
                parsed = {}
            for slug, companies in parsed.items():
                if slug not in curated_slugs:
                    continue
                company_map[slug].update(companies)
            fetched_company_sources.append(source["id"])
            logger.info(f"  {source['id']}: matched {sum(1 for s in parsed if s in curated_slugs)} curated slugs")
            time.sleep(request_delay_sec)

    result: Dict[str, Dict[str, Any]] = {}
    for slug in sorted(curated_slugs):
        problem = by_slug[slug]
        signals = sorted(source_membership.get(slug, set()))
        companies = sorted(company_map.get(slug, set()))
        overlap_bonus = 1.5 if problem.get("in_both") else 0.0
        frequency_tier = compute_frequency_tier(signals, companies, overlap_bonus)
        result[slug] = {
            "companies": companies,
            "frequency_tier": frequency_tier,
            "last_seen": str(datetime.now(timezone.utc).year),
            "follow_ups": FOLLOW_UP_HINTS.get(slug, []),
            "source_signals": signals,
            "interview_lists_count": len(signals),
            "company_count": len(companies),
        }

    ai_used = False
    ai_provider = ""
    ai_model = ""
    if ai_enrich:
        from ai import AIAnalyzerFactory

        analyzer = AIAnalyzerFactory.create_default()
        ai_provider = analyzer.provider.value
        ai_model = analyzer.model_name
        ai_used = True
        logger.info(f"AI enrichment enabled: provider={ai_provider} model={ai_model} limit={ai_limit}")

        # Conservative mode should spend calls where deterministic coverage is weakest.
        # Priority:
        # 1) lower tier first
        # 2) fewer companies first
        # 3) fewer source signals first
        # 4) then by score descending (to enrich high-value unresolved items)
        ranked = sorted(
            curated_slugs,
            key=lambda slug: (
                TIER_RANK.get(result[slug]["frequency_tier"], 0),
                result[slug]["company_count"],
                result[slug]["interview_lists_count"],
                -float(by_slug[slug].get("score", 0)),
            ),
        )[: max(0, ai_limit)]

        for index, slug in enumerate(ranked, start=1):
            base = result[slug]
            enriched_json = ai_enrich_problem(
                analyzer=analyzer,
                problem=by_slug[slug],
                source_signals=base["source_signals"],
                companies=base["companies"],
                frequency_tier=base["frequency_tier"],
            )
            if not enriched_json:
                continue

            ai_companies = []
            for raw in enriched_json.get("companies", []):
                normalized = normalize_company_name(str(raw))
                if normalized:
                    ai_companies.append(normalized)
            combined_companies = sorted(set(base["companies"]) | set(ai_companies))

            combined_follow_ups = sorted(set(base["follow_ups"]) | {
                slugify(str(x)) for x in enriched_json.get("follow_ups", []) if str(x).strip()
            })

            ai_tier = str(enriched_json.get("frequency_tier", "")).strip().lower()
            if ai_tier not in TIER_RANK:
                ai_tier = base["frequency_tier"]
            merged_tier = max([base["frequency_tier"], ai_tier], key=lambda tier: TIER_RANK.get(tier, 0))

            base["companies"] = combined_companies
            base["follow_ups"] = combined_follow_ups
            base["frequency_tier"] = merged_tier
            base["company_count"] = len(combined_companies)
            base["ai_enriched"] = True

            if index % 10 == 0:
                logger.info(f"  AI enriched {index}/{len(ranked)}")
            time.sleep(0.25)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "meta": {
            "total_problems": len(result),
            "offline": offline,
            "fetched_interview_lists": fetched_lists,
            "fetched_company_sources": fetched_company_sources,
            "ai_enriched": ai_used,
            "ai_provider": ai_provider,
            "ai_model": ai_model,
        },
        "problems": result,
    }

    output_path = DATA_DIR / "company_frequency.json"
    output_path.write_text(json.dumps(output, indent=2))
    logger.info(f"Saved company frequency metadata to {output_path}")
    logger.info(
        "Coverage: %s problems with >=1 company tag",
        sum(1 for row in result.values() if row["companies"]),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse and build company frequency metadata")
    parser.add_argument("--offline", action="store_true", help="Skip remote sources and use local deterministic signals only")
    parser.add_argument("--ai-enrich", action="store_true", help="Use AI to enrich company/follow-up metadata")
    parser.add_argument("--ai-limit", type=int, default=80, help="Maximum number of problems to AI-enrich")
    parser.add_argument("--request-delay-sec", type=float, default=0.4, help="Delay between remote source requests")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(
        offline=args.offline,
        ai_enrich=args.ai_enrich,
        ai_limit=args.ai_limit,
        request_delay_sec=args.request_delay_sec,
    )
