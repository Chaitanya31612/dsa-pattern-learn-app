"""
Generate per-problem solution breakdowns for in-app learning.

Output:
- data/solution_breakdowns.json

Default mode is deterministic (no API usage).
Optional AI mode can enrich a subset with deeper, problem-specific content.
"""

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"

PATTERN_NAME_TO_ID = {
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

PSEUDOCODE_BY_PATTERN_ID = {
    "arrays-hashing": """class Solution {
    public int solve(int[] nums) {
        // Track required state in a hash map / set.
        Map<Integer, Integer> freq = new HashMap<>();
        int answer = 0;
        for (int num : nums) {
            // Update state for current number.
            freq.put(num, freq.getOrDefault(num, 0) + 1);
            // Use state to maintain best answer.
        }
        return answer;
    }
}""",
    "two-pointers": """class Solution {
    public int solve(int[] nums) {
        // Keep two pointers and move based on invariant.
        int left = 0, right = nums.length - 1;
        int answer = 0;
        while (left < right) {
            // Evaluate current pair / window.
            // Move one pointer to improve toward target condition.
        }
        return answer;
    }
}""",
    "sliding-window": """class Solution {
    public int solve(String s) {
        // Expand right pointer, shrink left to restore validity.
        int left = 0, answer = 0;
        Map<Character, Integer> count = new HashMap<>();
        for (int right = 0; right < s.length(); right++) {
            char ch = s.charAt(right);
            count.put(ch, count.getOrDefault(ch, 0) + 1);
            while (!windowIsValid(count)) {
                char drop = s.charAt(left++);
                count.put(drop, count.get(drop) - 1);
            }
            answer = Math.max(answer, right - left + 1);
        }
        return answer;
    }
}""",
    "stack": """class Solution {
    public int solve(int[] nums) {
        // Use stack to preserve monotonic / structural invariant.
        Deque<Integer> stack = new ArrayDeque<>();
        int answer = 0;
        for (int value : nums) {
            while (!stack.isEmpty() && shouldPop(stack.peek(), value)) {
                // Resolve work for popped index/value.
                stack.pop();
            }
            stack.push(value);
        }
        return answer;
    }
}""",
    "binary-search": """class Solution {
    public int solve(int[] nums, int target) {
        // Binary search over index or answer space.
        int lo = 0, hi = nums.length - 1;
        while (lo <= hi) {
            int mid = lo + (hi - lo) / 2;
            if (isGood(mid, nums, target)) {
                hi = mid - 1;
            } else {
                lo = mid + 1;
            }
        }
        return lo;
    }
}""",
    "linked-list": """class Solution {
    public ListNode solve(ListNode head) {
        // Use pointer rewiring / slow-fast pointers safely.
        ListNode dummy = new ListNode(0);
        dummy.next = head;
        ListNode prev = dummy, curr = head;
        while (curr != null) {
            // Update links in constant extra space.
            curr = curr.next;
        }
        return dummy.next;
    }
}""",
    "trees": """class Solution {
    public int solve(TreeNode root) {
        // DFS returns sub-result; combine on unwind.
        return dfs(root);
    }

    private int dfs(TreeNode node) {
        if (node == null) return 0;
        int left = dfs(node.left);
        int right = dfs(node.right);
        // Merge left/right child answers with current node.
        return combine(node, left, right);
    }
}""",
    "tries": """class Trie {
    private static class Node {
        Node[] next = new Node[26];
        boolean end;
    }
    private final Node root = new Node();

    public void insert(String word) {
        Node cur = root;
        for (char ch : word.toCharArray()) {
            int idx = ch - 'a';
            if (cur.next[idx] == null) cur.next[idx] = new Node();
            cur = cur.next[idx];
        }
        cur.end = true;
    }
}""",
    "heap-priority-queue": """class Solution {
    public int solve(int[] nums, int k) {
        // Keep a size-k heap for top-k style problems.
        PriorityQueue<Integer> heap = new PriorityQueue<>();
        for (int value : nums) {
            heap.offer(value);
            if (heap.size() > k) heap.poll();
        }
        return heap.peek();
    }
}""",
    "backtracking": """class Solution {
    public List<List<Integer>> solve(int[] nums) {
        List<List<Integer>> out = new ArrayList<>();
        backtrack(0, nums, new ArrayList<>(), out);
        return out;
    }

    private void backtrack(int i, int[] nums, List<Integer> path, List<List<Integer>> out) {
        if (isComplete(i, nums, path)) {
            out.add(new ArrayList<>(path));
            return;
        }
        for (int choice : choices(i, nums, path)) {
            path.add(choice);
            backtrack(nextIndex(i, choice), nums, path, out);
            path.remove(path.size() - 1);
        }
    }
}""",
    "graphs": """class Solution {
    public int solve(int n, List<List<Integer>> graph) {
        // BFS/DFS with visited to avoid revisits.
        boolean[] visited = new boolean[n];
        int components = 0;
        for (int node = 0; node < n; node++) {
            if (visited[node]) continue;
            components++;
            bfs(node, graph, visited);
        }
        return components;
    }
}""",
    "1d-dp": """class Solution {
    public int solve(int[] nums) {
        // Define dp[i] as best answer for prefix ending at i.
        int[] dp = new int[nums.length];
        dp[0] = baseValue(nums[0]);
        for (int i = 1; i < nums.length; i++) {
            dp[i] = transition(dp, nums, i);
        }
        return dp[nums.length - 1];
    }
}""",
    "2d-dp": """class Solution {
    public int solve(String a, String b) {
        // State on two dimensions (i, j).
        int[][] dp = new int[a.length() + 1][b.length() + 1];
        for (int i = 1; i <= a.length(); i++) {
            for (int j = 1; j <= b.length(); j++) {
                dp[i][j] = transition(dp, a, b, i, j);
            }
        }
        return dp[a.length()][b.length()];
    }
}""",
    "greedy": """class Solution {
    public int solve(int[] nums) {
        // Make locally optimal choice while preserving feasibility.
        int answer = 0;
        int state = 0;
        for (int value : nums) {
            if (shouldTake(value, state)) {
                state = update(state, value);
                answer++;
            }
        }
        return answer;
    }
}""",
    "intervals": """class Solution {
    public int[][] solve(int[][] intervals) {
        // Sort by start, then merge overlaps.
        Arrays.sort(intervals, (a, b) -> Integer.compare(a[0], b[0]));
        List<int[]> merged = new ArrayList<>();
        for (int[] cur : intervals) {
            if (merged.isEmpty() || merged.get(merged.size() - 1)[1] < cur[0]) {
                merged.add(new int[]{cur[0], cur[1]});
            } else {
                merged.get(merged.size() - 1)[1] = Math.max(merged.get(merged.size() - 1)[1], cur[1]);
            }
        }
        return merged.toArray(new int[0][]);
    }
}""",
    "bit-manipulation": """class Solution {
    public int solve(int[] nums) {
        // Build bitwise invariant (xor / bit count / mask).
        int acc = 0;
        for (int value : nums) {
            acc ^= value;
        }
        return acc;
    }
}""",
    "math-geometry": """class Solution {
    public int solve(int[] nums) {
        // Translate prompt into arithmetic / geometric invariant.
        int answer = 0;
        for (int value : nums) {
            // Update formula-driven state.
        }
        return answer;
    }
}""",
}

ALTERNATIVES_BY_PATTERN_ID = {
    "sliding-window": [
        {"approach": "Brute force all subarrays/substrings", "tradeoff": "Simple but usually O(n^2) or worse."},
        {"approach": "Prefix sum + hash map", "tradeoff": "Useful for exact-sum variants; less direct for dynamic constraints."},
    ],
    "binary-search": [
        {"approach": "Linear scan", "tradeoff": "Trivial but O(n), often too slow for large inputs."},
        {"approach": "Binary search on answer", "tradeoff": "Needs monotonic predicate proof before implementation."},
    ],
    "graphs": [
        {"approach": "DFS recursion", "tradeoff": "Compact but can hit recursion depth on deep graphs."},
        {"approach": "BFS iterative queue", "tradeoff": "Stable and explicit levels, but queue memory can spike."},
    ],
}

DEFAULT_ALTERNATIVES = [
    {"approach": "Brute force baseline", "tradeoff": "Good for validation, usually fails interview constraints."},
    {"approach": "Pattern-optimized approach", "tradeoff": "Requires maintaining strict invariants but gives target complexity."},
]

TIER_HINT = {
    "Easy": "Keep the implementation minimal and prioritize correctness checks first.",
    "Medium": "Focus on invariant maintenance and boundary updates each iteration.",
    "Hard": "Derive state transitions explicitly before coding to avoid hidden edge-case bugs.",
}


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def strip_code_fences(text: str) -> str:
    payload = text.strip()
    if payload.startswith("```"):
        payload = payload.split("\n", 1)[1] if "\n" in payload else payload
        if payload.endswith("```"):
            payload = payload[:-3]
    return payload.strip()


def pattern_id_for_problem(problem: dict) -> str:
    pattern_name = problem.get("pattern", "")
    return PATTERN_NAME_TO_ID.get(pattern_name, str(pattern_name).lower().replace(" ", "-"))


def fallback_pseudocode(pattern_id: str) -> str:
    return PSEUDOCODE_BY_PATTERN_ID.get(
        pattern_id,
        """class Solution {
    public int solve(int[] nums) {
        // Define invariant/state and update it per element.
        int answer = 0;
        for (int x : nums) {
            // Apply transition.
        }
        return answer;
    }
}""",
    )


def deterministic_breakdown(problem: dict, insight: dict, pattern_context: dict) -> Dict[str, Any]:
    pattern_name = problem.get("pattern", "Unknown")
    pattern_id = pattern_id_for_problem(problem)
    title = problem.get("title", "")
    difficulty = problem.get("difficulty")

    pattern_hint = normalize_text(insight.get("pattern_hint"))
    key_insight = normalize_text(insight.get("key_insight"))
    template_deviation = normalize_text(insight.get("template_deviation"))
    common_mistake = normalize_text(insight.get("common_mistake"))
    time_complexity = normalize_text(insight.get("time_complexity"))
    space_complexity = normalize_text(insight.get("space_complexity"))

    mental_model = normalize_text(pattern_context.get("mental_model"))
    explanation = normalize_text(pattern_context.get("explanation"))
    pattern_use = pattern_context.get("when_to_use") or []
    pattern_signal = normalize_text(pattern_use[0] if pattern_use else "")

    intuition = key_insight or (
        f"Treat this as a {pattern_name} problem and keep the core invariant stable after every update."
    )
    pattern_connection = (
        f"This maps to {pattern_name} because {pattern_hint.lower() if pattern_hint else 'the constraints and structure favor this pattern'}."
    )
    if mental_model:
        pattern_connection += f" Mental model: {mental_model}"
    elif explanation:
        pattern_connection += f" {explanation[:180]}..."

    steps = [
        {
            "title": "Identify the signal",
            "detail": pattern_hint or pattern_signal or f"Look for cues that suggest {pattern_name}.",
        },
        {
            "title": "Set up the core invariant",
            "detail": (
                f"Choose data/state so each transition preserves correctness for {title}."
                if title
                else f"Choose data/state so each transition preserves correctness."
            ),
        },
        {
            "title": "Run transitions and update answer",
            "detail": template_deviation or "Apply the standard template and adjust update conditions for this prompt.",
        },
        {
            "title": "Validate complexity and boundaries",
            "detail": (
                f"Target {time_complexity or 'optimal time'} and {space_complexity or 'optimal space'}, then test edge cases."
            ),
        },
    ]

    edge_cases = [
        "Empty input or single-element input.",
        "Duplicate values and repeated states.",
        "Boundary indices (first/last element, full-window/full-range cases).",
    ]
    if common_mistake:
        edge_cases.append(f"Guard against this common pitfall: {common_mistake}")
    diff_hint = TIER_HINT.get(difficulty or "", "")
    if diff_hint:
        edge_cases.append(diff_hint)

    alternatives = ALTERNATIVES_BY_PATTERN_ID.get(pattern_id, DEFAULT_ALTERNATIVES)

    return {
        "intuition": intuition,
        "pattern_connection": pattern_connection,
        "steps": steps,
        "java_pseudocode": fallback_pseudocode(pattern_id),
        "edge_cases": edge_cases[:6],
        "alternatives": alternatives,
        "source": "deterministic",
    }


def ai_breakdown(analyzer, problem: dict, insight: dict, deterministic: dict) -> Dict[str, Any]:
    prompt = (
        "You are an expert DSA tutor. Create a concise structured solution breakdown.\n"
        "Return ONLY valid JSON with this schema:\n"
        "{"
        "\"intuition\":\"string\","
        "\"pattern_connection\":\"string\","
        "\"steps\":[{\"title\":\"string\",\"detail\":\"string\"}],"
        "\"java_pseudocode\":\"string\","
        "\"edge_cases\":[\"string\"],"
        "\"alternatives\":[{\"approach\":\"string\",\"tradeoff\":\"string\"}]"
        "}\n"
        "Rules:\n"
        "- 4 to 6 steps\n"
        "- java_pseudocode must be Java-like and include comments\n"
        "- keep edge_cases max 6\n"
        "- keep alternatives max 3"
    )
    content = (
        f"Problem: {problem.get('title', '')} ({problem.get('slug', '')})\n"
        f"Pattern: {problem.get('pattern', '')}\n"
        f"Difficulty: {problem.get('difficulty', '')}\n"
        f"Pattern hint: {insight.get('pattern_hint', '')}\n"
        f"Key insight: {insight.get('key_insight', '')}\n"
        f"Common mistake: {insight.get('common_mistake', '')}\n"
        f"Current deterministic breakdown: {json.dumps(deterministic)}\n"
    )

    response = analyzer.analyze(content=content, prompt=prompt)
    if not response.success or not response.content:
        return {}

    try:
        payload = json.loads(strip_code_fences(response.content))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def sanitize_ai_payload(raw: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(fallback)
    intuition = normalize_text(raw.get("intuition"))
    pattern_connection = normalize_text(raw.get("pattern_connection"))
    java_pseudocode = normalize_text(raw.get("java_pseudocode"))

    if intuition:
        result["intuition"] = intuition
    if pattern_connection:
        result["pattern_connection"] = pattern_connection
    if java_pseudocode:
        result["java_pseudocode"] = java_pseudocode

    raw_steps = raw.get("steps", [])
    if isinstance(raw_steps, list):
        clean_steps = []
        for step in raw_steps:
            if not isinstance(step, dict):
                continue
            title = normalize_text(step.get("title"))
            detail = normalize_text(step.get("detail"))
            if title and detail:
                clean_steps.append({"title": title, "detail": detail})
        if clean_steps:
            result["steps"] = clean_steps[:6]

    raw_edges = raw.get("edge_cases", [])
    if isinstance(raw_edges, list):
        clean_edges = [normalize_text(item) for item in raw_edges if normalize_text(item)]
        if clean_edges:
            result["edge_cases"] = clean_edges[:6]

    raw_alts = raw.get("alternatives", [])
    if isinstance(raw_alts, list):
        clean_alts = []
        for alt in raw_alts:
            if not isinstance(alt, dict):
                continue
            approach = normalize_text(alt.get("approach"))
            tradeoff = normalize_text(alt.get("tradeoff"))
            if approach and tradeoff:
                clean_alts.append({"approach": approach, "tradeoff": tradeoff})
        if clean_alts:
            result["alternatives"] = clean_alts[:3]

    result["source"] = "ai"
    return result


def run(
    ai_enrich: bool = False,
    ai_limit: int = 40,
    ai_provider: str = "auto",
    request_delay_sec: float = 0.25,
):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    enriched = load_json(DATA_DIR / "enriched_problems.json")
    patterns = load_json(DATA_DIR / "patterns.json")
    insights = load_json(DATA_DIR / "problem_insights.json")
    if not enriched or not patterns or not insights:
        logger.error("Missing required files. Run fetch_leetcode.py, generate_patterns.py, generate_problem_insights.py first.")
        return

    insights_by_slug = {row.get("slug"): row for row in insights if isinstance(row, dict) and row.get("slug")}
    patterns_by_id = {row.get("pattern_id"): row for row in patterns if isinstance(row, dict) and row.get("pattern_id")}

    result: Dict[str, Dict[str, Any]] = {}
    for problem in enriched:
        slug = problem.get("slug")
        if not slug:
            continue
        pattern_id = pattern_id_for_problem(problem)
        insight = insights_by_slug.get(slug, {})
        pattern_context = patterns_by_id.get(pattern_id, {})
        result[slug] = deterministic_breakdown(problem, insight, pattern_context)

    ai_used = False
    ai_provider_used = ""
    ai_model = ""
    ai_enriched_count = 0

    if ai_enrich:
        from ai import AIAnalyzerFactory, AIProvider

        ai_used = True
        provider_map = {
            "groq": AIProvider.GROQ,
            "gemini": AIProvider.GEMINI,
            "ollama": AIProvider.OLLAMA,
        }
        if ai_provider in provider_map:
            analyzer = AIAnalyzerFactory.create(provider_map[ai_provider])
        else:
            analyzer = AIAnalyzerFactory.create_default()

        ai_provider_used = analyzer.provider.value
        ai_model = analyzer.model_name
        logger.info(f"AI enrichment enabled: provider={ai_provider_used} model={ai_model} limit={ai_limit}")

        ranked = sorted(
            [p for p in enriched if p.get("slug") in result],
            key=lambda p: float(p.get("score", 0)),
            reverse=True,
        )[: max(0, ai_limit)]

        for index, problem in enumerate(ranked, start=1):
            slug = problem.get("slug")
            if not slug:
                continue
            enriched_json = ai_breakdown(
                analyzer=analyzer,
                problem=problem,
                insight=insights_by_slug.get(slug, {}),
                deterministic=result[slug],
            )
            if not enriched_json:
                continue
            result[slug] = sanitize_ai_payload(enriched_json, result[slug])
            ai_enriched_count += 1
            if index % 10 == 0:
                logger.info(f"  AI enriched {index}/{len(ranked)}")
            time.sleep(max(request_delay_sec, 0.05))

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "meta": {
            "total_problems": len(result),
            "ai_enriched": ai_used,
            "ai_provider": ai_provider_used,
            "ai_model": ai_model,
            "ai_enriched_count": ai_enriched_count,
        },
        "problems": result,
    }
    output_path = DATA_DIR / "solution_breakdowns.json"
    output_path.write_text(json.dumps(output, indent=2))
    logger.info(f"Saved solution breakdowns to {output_path}")
    logger.info(f"Coverage: {len(result)} problems")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate per-problem solution breakdowns")
    parser.add_argument("--ai-enrich", action="store_true", help="Use AI to enrich deterministic breakdowns")
    parser.add_argument("--ai-limit", type=int, default=40, help="Maximum number of problems to AI-enrich")
    parser.add_argument(
        "--ai-provider",
        type=str,
        choices=["auto", "groq", "gemini", "ollama"],
        default="auto",
        help="AI provider to use when --ai-enrich is enabled",
    )
    parser.add_argument("--request-delay-sec", type=float, default=0.25, help="Delay between AI requests")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(
        ai_enrich=args.ai_enrich,
        ai_limit=args.ai_limit,
        ai_provider=args.ai_provider,
        request_delay_sec=args.request_delay_sec,
    )
