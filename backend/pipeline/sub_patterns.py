"""
Shared sub-pattern taxonomy + lightweight keyword rules.

Used by:
- generate_patterns.py (schema generation)
- build_final_db.py (problem -> sub-pattern mapping)
"""

from copy import deepcopy
from typing import Any, Dict, List


SUB_PATTERN_SCHEMA: Dict[str, List[Dict[str, Any]]] = {
    "arrays-hashing": [
        {
            "sub_pattern_id": "frequency-counting",
            "name": "Frequency Counting",
            "description": "Count occurrences with hash maps or fixed-size arrays to answer membership and frequency questions quickly.",
            "trigger_phrases": ["count", "frequency", "anagram", "duplicate"],
        },
        {
            "sub_pattern_id": "index-mapping",
            "name": "Index Mapping",
            "description": "Store value->index relationships to support constant-time lookups while scanning once.",
            "trigger_phrases": ["indices", "target sum", "first occurrence", "lookup table"],
        },
        {
            "sub_pattern_id": "set-membership",
            "name": "Set Membership",
            "description": "Use sets for O(1)-average membership checks when order is less important than existence.",
            "trigger_phrases": ["contains", "exists", "seen before", "unique"],
        },
        {
            "sub_pattern_id": "prefix-bucket-techniques",
            "name": "Prefix / Bucket Techniques",
            "description": "Combine prefix aggregates or bucketized counts for range queries and near-linear grouping.",
            "trigger_phrases": ["prefix sum", "range query", "bucket", "group by"],
        },
    ],
    "two-pointers": [
        {
            "sub_pattern_id": "opposite-direction",
            "name": "Opposite Direction Pointers",
            "description": "Start from both ends and move inward based on comparisons.",
            "trigger_phrases": ["sorted array", "pair sum", "container", "palindrome"],
        },
        {
            "sub_pattern_id": "same-direction-fast-slow",
            "name": "Same Direction Fast-Slow",
            "description": "Move pointers at different speeds or roles in one pass.",
            "trigger_phrases": ["fast and slow", "cycle", "remove duplicates", "in-place scan"],
        },
        {
            "sub_pattern_id": "partitioning",
            "name": "Partitioning",
            "description": "Rearrange elements around pivots/conditions with pointer swaps.",
            "trigger_phrases": ["partition", "sort colors", "segregate", "pivot"],
        },
    ],
    "sliding-window": [
        {
            "sub_pattern_id": "fixed-window",
            "name": "Fixed Window",
            "description": "Maintain a constant-size window while moving across the sequence.",
            "trigger_phrases": ["size k", "window of length", "average", "maximum sum"],
        },
        {
            "sub_pattern_id": "variable-window",
            "name": "Variable Window",
            "description": "Expand and shrink bounds to satisfy constraints optimally.",
            "trigger_phrases": ["longest", "smallest", "at most", "at least"],
        },
        {
            "sub_pattern_id": "monotonic-deque-window",
            "name": "Monotonic Deque Window",
            "description": "Track window extrema with a monotonic deque for O(n) updates.",
            "trigger_phrases": ["sliding window maximum", "minimum in window", "deque"],
        },
    ],
    "stack": [
        {
            "sub_pattern_id": "monotonic-stack",
            "name": "Monotonic Stack",
            "description": "Maintain ordered stack states to find previous/next greater-or-smaller elements.",
            "trigger_phrases": ["next greater", "daily temperatures", "histogram", "stock span"],
        },
        {
            "sub_pattern_id": "expression-evaluation",
            "name": "Expression Evaluation",
            "description": "Evaluate or transform expressions using operator/operand stack mechanics.",
            "trigger_phrases": ["evaluate", "calculator", "postfix", "infix", "RPN"],
        },
        {
            "sub_pattern_id": "nested-structures",
            "name": "Nested Structures",
            "description": "Use stack depth to parse balanced/nested constructs.",
            "trigger_phrases": ["parentheses", "brackets", "nested", "decode string"],
        },
    ],
    "binary-search": [
        {
            "sub_pattern_id": "sorted-array-search",
            "name": "Classic Sorted Search",
            "description": "Binary search directly on sorted indexes for exact/first/last answers.",
            "trigger_phrases": ["sorted", "find target", "lower bound", "upper bound"],
        },
        {
            "sub_pattern_id": "binary-search-on-answer",
            "name": "Binary Search on Answer",
            "description": "Search the feasible answer range using a monotonic predicate.",
            "trigger_phrases": ["minimum possible", "maximize", "feasible", "capacity"],
        },
        {
            "sub_pattern_id": "rotated-search-space",
            "name": "Rotated Search Space",
            "description": "Exploit partially sorted halves in rotated/shifted arrays.",
            "trigger_phrases": ["rotated", "pivot", "minimum in rotated", "search rotated"],
        },
    ],
    "linked-list": [
        {
            "sub_pattern_id": "pointer-manipulation",
            "name": "Pointer Manipulation",
            "description": "Update next/random pointers carefully using dummy/predecessor nodes.",
            "trigger_phrases": ["merge lists", "remove node", "dummy head", "relink"],
        },
        {
            "sub_pattern_id": "fast-slow-cycles",
            "name": "Fast-Slow / Cycle Detection",
            "description": "Use tortoise-hare style traversal to detect cycles or midpoint properties.",
            "trigger_phrases": ["cycle", "middle node", "intersection", "fast and slow"],
        },
        {
            "sub_pattern_id": "in-place-reversal",
            "name": "In-place Reversal",
            "description": "Reverse whole or partial list segments by pointer rewiring.",
            "trigger_phrases": ["reverse list", "reverse k group", "reorder list", "swap pairs"],
        },
    ],
    "trees": [
        {
            "sub_pattern_id": "dfs-recursive",
            "name": "DFS Recursive",
            "description": "Traverse or compute tree states via preorder/inorder/postorder recursion.",
            "trigger_phrases": ["recursive", "depth-first", "subtree", "postorder"],
        },
        {
            "sub_pattern_id": "bfs-level-order",
            "name": "BFS Level Order",
            "description": "Process nodes level by level using queues.",
            "trigger_phrases": ["level order", "right side view", "minimum depth", "queue"],
        },
        {
            "sub_pattern_id": "bst-operations",
            "name": "BST-specific",
            "description": "Leverage BST ordering for search/insert/validation/range operations.",
            "trigger_phrases": ["BST", "validate BST", "kth smallest", "inorder sorted"],
        },
        {
            "sub_pattern_id": "path-aggregation",
            "name": "Path Aggregation",
            "description": "Track cumulative path state for sum/diameter/max-path style problems.",
            "trigger_phrases": ["path sum", "diameter", "max path", "root to leaf"],
        },
    ],
    "tries": [
        {
            "sub_pattern_id": "prefix-query",
            "name": "Prefix Query Trie",
            "description": "Build prefix tree for efficient prefix/exact word lookup.",
            "trigger_phrases": ["prefix", "autocomplete", "starts with", "dictionary"],
        },
        {
            "sub_pattern_id": "wildcard-trie-search",
            "name": "Wildcard Trie Search",
            "description": "Use branching DFS in trie when wildcard characters appear.",
            "trigger_phrases": ["wildcard", "dot", "regex-like", "word dictionary"],
        },
        {
            "sub_pattern_id": "bitwise-trie",
            "name": "Bitwise Trie",
            "description": "Store binary representations in trie for XOR maximization/minimization.",
            "trigger_phrases": ["maximum xor", "bitwise trie", "binary prefix"],
        },
    ],
    "heap-priority-queue": [
        {
            "sub_pattern_id": "top-k-selection",
            "name": "Top-K Selection",
            "description": "Keep bounded heap to retrieve top/bottom K elements efficiently.",
            "trigger_phrases": ["top k", "k closest", "k frequent", "smallest k"],
        },
        {
            "sub_pattern_id": "stream-heap",
            "name": "Stream Heap",
            "description": "Continuously update heap as stream values arrive.",
            "trigger_phrases": ["data stream", "kth largest", "online", "real-time updates"],
        },
        {
            "sub_pattern_id": "two-heap-balancing",
            "name": "Two-Heap Balancing",
            "description": "Use max/min heap pair to maintain dynamic median partitions.",
            "trigger_phrases": ["median", "two heaps", "balance halves"],
        },
    ],
    "backtracking": [
        {
            "sub_pattern_id": "subset-combination",
            "name": "Subset / Combination Search",
            "description": "Explore include/exclude or choose-next states for combinations.",
            "trigger_phrases": ["subsets", "combination sum", "choose k", "power set"],
        },
        {
            "sub_pattern_id": "permutation-ordering",
            "name": "Permutation Ordering",
            "description": "Generate order-sensitive arrangements with used-state tracking.",
            "trigger_phrases": ["permutations", "arrangements", "ordering"],
        },
        {
            "sub_pattern_id": "constraint-backtracking",
            "name": "Constraint Satisfaction",
            "description": "Prune search using validity checks at every decision point.",
            "trigger_phrases": ["N-Queens", "sudoku", "word search", "constraints"],
        },
    ],
    "graphs": [
        {
            "sub_pattern_id": "bfs-dfs-traversal",
            "name": "BFS / DFS Traversal",
            "description": "Traverse graph components/paths with visitation tracking.",
            "trigger_phrases": ["connected components", "visit all nodes", "islands", "traversal"],
        },
        {
            "sub_pattern_id": "topological-ordering",
            "name": "Topological Ordering",
            "description": "Order DAG nodes by dependency constraints via indegree or DFS stack.",
            "trigger_phrases": ["course schedule", "prerequisite", "DAG", "dependency"],
        },
        {
            "sub_pattern_id": "union-find-connectivity",
            "name": "Union-Find (DSU)",
            "description": "Track dynamic connectivity and component merges with DSU.",
            "trigger_phrases": ["union find", "disjoint set", "connected", "redundant edge"],
        },
        {
            "sub_pattern_id": "shortest-path",
            "name": "Shortest Path",
            "description": "Compute shortest distances with BFS/Dijkstra variants.",
            "trigger_phrases": ["shortest path", "minimum cost", "weighted graph", "dijkstra"],
        },
        {
            "sub_pattern_id": "multi-source-bfs",
            "name": "Multi-Source BFS",
            "description": "Initialize BFS queue with multiple starts for nearest-distance fills.",
            "trigger_phrases": ["nearest", "rotting oranges", "walls and gates", "multiple sources"],
        },
    ],
    "1d-dp": [
        {
            "sub_pattern_id": "linear-state-dp",
            "name": "Linear State DP",
            "description": "Transition from previous states along one dimension.",
            "trigger_phrases": ["climb stairs", "house robber", "fibonacci", "one-dimensional states"],
        },
        {
            "sub_pattern_id": "knapsack-style-dp",
            "name": "Knapsack-style DP",
            "description": "Choose/take-skip decisions over capacity/target constraints.",
            "trigger_phrases": ["target sum", "subset sum", "coin change", "capacity"],
        },
        {
            "sub_pattern_id": "state-machine-dp",
            "name": "State Machine DP",
            "description": "Model transitions among limited states such as buy/sell/hold.",
            "trigger_phrases": ["stock", "cooldown", "transaction", "state transitions"],
        },
        {
            "sub_pattern_id": "lis-variant-dp",
            "name": "LIS Variants",
            "description": "Optimize increasing/decreasing subsequence style transitions.",
            "trigger_phrases": ["LIS", "subsequence", "increasing", "patience sorting"],
        },
    ],
    "2d-dp": [
        {
            "sub_pattern_id": "grid-dp",
            "name": "Grid DP",
            "description": "Dynamic programming on cells with directional transitions.",
            "trigger_phrases": ["grid", "matrix path", "unique paths", "minimum path sum"],
        },
        {
            "sub_pattern_id": "sequence-alignment-dp",
            "name": "Two-Sequence DP",
            "description": "DP table over two strings/sequences for match/edit operations.",
            "trigger_phrases": ["LCS", "edit distance", "interleaving string", "two strings"],
        },
        {
            "sub_pattern_id": "interval-dp",
            "name": "Interval DP",
            "description": "Solve over subarray ranges while expanding interval length.",
            "trigger_phrases": ["burst balloons", "palindrome partition", "interval"],
        },
    ],
    "greedy": [
        {
            "sub_pattern_id": "local-choice-scheduling",
            "name": "Local Choice Scheduling",
            "description": "Pick the locally best option at each step with proof of global optimality.",
            "trigger_phrases": ["schedule", "maximize count", "min arrows", "sort by end"],
        },
        {
            "sub_pattern_id": "interval-selection",
            "name": "Interval Selection",
            "description": "Sort intervals and select/merge greedily based on boundaries.",
            "trigger_phrases": ["interval", "overlap", "erase", "merge"],
        },
        {
            "sub_pattern_id": "jump-and-reachability",
            "name": "Jump / Reachability",
            "description": "Track farthest reachable frontier with greedy updates.",
            "trigger_phrases": ["jump game", "reach end", "minimum jumps"],
        },
    ],
    "intervals": [
        {
            "sub_pattern_id": "merge-overlaps",
            "name": "Merge Overlaps",
            "description": "Sort by start and merge intersecting intervals.",
            "trigger_phrases": ["merge intervals", "insert interval", "overlap"],
        },
        {
            "sub_pattern_id": "sweep-line-events",
            "name": "Sweep Line Events",
            "description": "Convert boundaries into entry/exit events and scan.",
            "trigger_phrases": ["line sweep", "events", "timeline"],
        },
        {
            "sub_pattern_id": "meeting-room-allocation",
            "name": "Meeting Room Allocation",
            "description": "Track concurrent intervals to compute required resources.",
            "trigger_phrases": ["meeting rooms", "min rooms", "calendar", "overlapping meetings"],
        },
    ],
    "bit-manipulation": [
        {
            "sub_pattern_id": "xor-identities",
            "name": "XOR Identities",
            "description": "Use XOR cancelation and bit tricks for unique/missing element tasks.",
            "trigger_phrases": ["single number", "xor", "missing number"],
        },
        {
            "sub_pattern_id": "bitmask-state",
            "name": "Bitmask State",
            "description": "Represent subsets/states compactly with bitmasks.",
            "trigger_phrases": ["bitmask", "subset mask", "state compression"],
        },
        {
            "sub_pattern_id": "bit-counting",
            "name": "Bit Counting",
            "description": "Count or transform set bits using lowbit operations.",
            "trigger_phrases": ["count bits", "hamming", "set bits", "power of two"],
        },
    ],
    "math-geometry": [
        {
            "sub_pattern_id": "coordinate-geometry",
            "name": "Coordinate Geometry",
            "description": "Compute distances/slopes/areas using geometric invariants.",
            "trigger_phrases": ["points", "line", "distance", "slope", "area"],
        },
        {
            "sub_pattern_id": "matrix-simulation",
            "name": "Matrix Simulation",
            "description": "Traverse or transform 2D grids with directional simulation.",
            "trigger_phrases": ["spiral", "rotate matrix", "simulate", "grid movement"],
        },
        {
            "sub_pattern_id": "number-theory",
            "name": "Number Theory",
            "description": "Apply arithmetic properties such as gcd/mod/primes.",
            "trigger_phrases": ["gcd", "prime", "mod", "power", "roman"],
        },
    ],
}


SUB_PATTERN_KEYWORDS: Dict[str, List[str]] = {
    "frequency-counting": ["frequency", "anagram", "duplicate", "majority", "count"],
    "index-mapping": ["two sum", "index", "mapping", "lookup"],
    "set-membership": ["contains", "consecutive", "unique", "seen"],
    "prefix-bucket-techniques": ["prefix", "bucket", "range", "subarray sum", "counting sort"],
    "opposite-direction": ["palindrome", "container", "sorted", "pair"],
    "same-direction-fast-slow": ["fast", "slow", "duplicate", "remove", "cycle"],
    "partitioning": ["partition", "sort colors", "pivot", "segregate"],
    "fixed-window": ["window", "size k", "fixed", "average"],
    "variable-window": ["longest", "smallest", "at most", "at least", "substring"],
    "monotonic-deque-window": ["deque", "window maximum", "monotonic queue"],
    "monotonic-stack": ["monotonic stack", "next greater", "daily temperatures", "histogram", "stock span"],
    "expression-evaluation": ["evaluate", "calculator", "rpn", "postfix", "infix"],
    "nested-structures": ["parentheses", "nested", "brackets", "decode string"],
    "sorted-array-search": ["binary search", "sorted", "lower bound", "upper bound"],
    "binary-search-on-answer": ["minimum possible", "maximize", "capacity", "feasible", "koko"],
    "rotated-search-space": ["rotated", "pivot"],
    "pointer-manipulation": ["merge", "dummy", "random pointer", "relink"],
    "fast-slow-cycles": ["cycle", "middle", "intersection", "fast and slow"],
    "in-place-reversal": ["reverse", "reorder", "swap pairs", "k group"],
    "dfs-recursive": ["depth-first", "dfs", "recursive", "subtree"],
    "bfs-level-order": ["level order", "breadth-first", "queue", "right side view"],
    "bst-operations": ["bst", "binary search tree", "kth smallest", "validate"],
    "path-aggregation": ["path sum", "diameter", "max path", "root to leaf"],
    "prefix-query": ["trie", "prefix", "starts with", "dictionary"],
    "wildcard-trie-search": ["wildcard", "word dictionary", "dot"],
    "bitwise-trie": ["xor", "bitwise trie", "binary trie"],
    "top-k-selection": ["top k", "kth", "closest", "frequent"],
    "stream-heap": ["stream", "online", "kth largest"],
    "two-heap-balancing": ["median", "two heaps"],
    "subset-combination": ["subset", "combination", "choose"],
    "permutation-ordering": ["permutation", "arrange", "ordering"],
    "constraint-backtracking": ["sudoku", "n-queens", "word search", "constraint"],
    "bfs-dfs-traversal": ["islands", "components", "traversal", "dfs", "bfs"],
    "topological-ordering": ["course schedule", "topological", "prerequisite", "dag"],
    "union-find-connectivity": ["union-find", "disjoint set", "connected", "redundant"],
    "shortest-path": ["shortest path", "dijkstra", "minimum cost", "weighted"],
    "multi-source-bfs": ["rotting oranges", "walls and gates", "nearest", "multi-source"],
    "linear-state-dp": ["fibonacci", "house robber", "stairs", "linear dp"],
    "knapsack-style-dp": ["coin change", "subset sum", "target sum", "knapsack"],
    "state-machine-dp": ["stock", "transaction", "cooldown", "state machine"],
    "lis-variant-dp": ["lis", "increasing subsequence", "patience"],
    "grid-dp": ["grid", "matrix", "path sum", "unique paths"],
    "sequence-alignment-dp": ["lcs", "edit distance", "interleaving", "two strings"],
    "interval-dp": ["interval dp", "burst balloons", "partition"],
    "local-choice-scheduling": ["schedule", "assign", "maximize", "minimize"],
    "interval-selection": ["interval", "overlap", "erase", "merge"],
    "jump-and-reachability": ["jump game", "reachability", "farthest"],
    "merge-overlaps": ["merge intervals", "insert interval", "overlap"],
    "sweep-line-events": ["sweep", "event", "timeline"],
    "meeting-room-allocation": ["meeting", "calendar", "rooms"],
    "xor-identities": ["xor", "single number", "missing number"],
    "bitmask-state": ["bitmask", "mask", "state compression"],
    "bit-counting": ["count bits", "hamming", "set bits", "power of two"],
    "coordinate-geometry": ["point", "line", "slope", "distance", "geometry"],
    "matrix-simulation": ["matrix", "spiral", "rotate image", "simulation"],
    "number-theory": ["gcd", "prime", "mod", "power", "roman"],
}


def get_sub_patterns_for_pattern(pattern_id: str) -> List[Dict[str, Any]]:
    """Return a safe copy of configured sub-patterns for a pattern ID."""
    return deepcopy(SUB_PATTERN_SCHEMA.get(pattern_id, []))
