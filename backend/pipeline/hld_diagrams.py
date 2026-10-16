"""Original teaching visuals aligned with the course, not copied book figures."""
VISUALS = {}


def pair(slug, overview, recap, caption):
    # Overview flows read down the page so the whole story fits a lesson column.
    overview = overview.replace('flowchart LR', 'flowchart TD')
    VISUALS[slug] = [
        {'id': 'overview', 'title': 'See the mechanism first', 'caption': caption, 'placement': 'overview', 'code': overview},
        {'id': 'recap', 'title': 'The complete module at a glance', 'caption': 'Explain each arrow from memory. Check the lesson only after you try.', 'placement': 'recap', 'code': recap},
    ]


pair('00-design-framework', '''flowchart LR
 C["Contract"] --> S["Size"] --> M["Model"] --> F["Flow"] --> T["Stress"] --> O["Operate"] --> E["Explain"]''', '''flowchart TD
 P["Ambiguous product prompt"] --> C["Contract: user, scope, NFR, invariant"]
 C --> S["Size: rates, bytes, connections; only useful estimates"]
 S --> M["Model: API, source of truth, keys, atomic boundary"]
 M --> F["Flow: write and read; durable success point"]
 F --> T["Stress: concurrency, crash, skew, stale data"]
 T --> O["Operate: metrics, recovery, security, cost, rollout"]
 O --> E["Explain: choice, alternative, downside, next limit"]
 T --> R["Changed requirement"] --> C
 E --> V["Save attempt; feedback; delayed transfer"]''', 'One stable presentation structure; select the deep dive from the actual problem.')

pair('01-request-scale-estimation', '''flowchart LR
 C["Client"] --> N["DNS and connection"] --> L["Edge or load balancer"] --> A["Application"] --> P["Connection pool"] --> D[("Database")]
 A --> X["External dependency"]''', '''flowchart TD
 U["Users and operations per user"] --> Q["Average operations per second"] --> K["Peak and amplification"]
 Q --> W["Arrival rate x mean residence time"] --> I["Mean in-flight work"]
 B["Object size x new objects x retention"] --> S["Raw storage; add indexes and copies"]
 K --> N["Bytes per operation"] --> E["Network bytes and bits per second"]
 K --> M["Measure wait and service time"] --> R["Find actual bottleneck"]
 R --> H["Simplest intervention and headroom"] --> T["Test skew, cold cache, and failure"]''', 'Trace waits as well as computing. Low CPU can coexist with a slow request.')

pair('02-data-cache-correctness', '''flowchart LR
 A["Client A"] --> C["Atomic authoritative claim"]
 B["Client B"] --> C
 C --> D[("Inventory and operation identity")]
 D --> W["One winner"]
 D --> L["Other client gets conflict"]''', '''flowchart TD
 R["Access patterns and invariant"] --> K["Keys, indexes, ownership"] --> D[("Authoritative state")]
 D --> T["Conditional update or suitable transaction"] --> I["Retry identity and recorded result"]
 D --> C["Derived cache: TTL and versions"] --> F["Freshness and stale-fill race"]
 C --> O["Cold-cache fallback; coalescing; admission"]
 I --> P["External effect outside local transaction"] --> X["Unknown outcome: reconcile with provider"]
 D --> B["Replication plus tested backup restore"]''', 'Separate approximate reads, authoritative claims, and external-effect uncertainty.')

pair('03-url-shortener', '''flowchart LR
 C["Create link"] --> A["Owner-authorized API"] --> D[("Unique code mapping")]
 V["Visit short link"] --> R["Redirect service"] --> K[("Bounded cache")]
 K -->|"miss"| D
 D --> R --> T["Live target and redirect"]''', '''flowchart TD
 P["Mutable or immutable? Expiry? Ownership?"] --> I["Code generation and unique insertion"] --> D[("Mapping, version, expiry, owner")]
 V["Visit code"] --> C["Client, edge, and application cache policy"] --> D
 D --> A["Check expiry and access"] --> R["Redirect"] --> E["Best-effort analytics if permitted"]
 P --> U["Edit or revoke"] --> D
 U --> F["Freshness across every serving layer"] --> C
 C --> X["Cache loss or viral code"] --> B["Bounded fallback and coalescing"]
 D --> M["Compatible generator and storage migrations"]''', 'Create and redirect are different flows. Edits change the caching contract.')

pair('04-unique-ids', '''flowchart LR
 T["Safe elapsed timestamp"] --> C["Compose ID"]
 W["Unique fenced worker identity"] --> C
 S["Sequence within timestamp"] --> C --> I["Unique under stated assumptions"]''', '''flowchart TD
 R["Required uniqueness and ordering"] --> A["Random, allocated range, or time-based"]
 A --> W["Worker or range ownership"] --> T["Timestamp and last emitted state"]
 T --> B{"Clock moved backwards?"}
 B -->|"yes"| F["Wait, fail, or coordinated alternative"]
 B -->|"no"| S{"Sequence exhausted?"}
 S -->|"yes"| P["Backpressure; never silently wrap"]
 S -->|"no"| C["Emit and preserve restart safety"]
 C --> O["Rough time order is not causal order"]
 R --> G["Strict global numbering needs coordinated authority"]''', 'Bit layout is only part of the design; worker ownership and rollback determine safety.')

pair('05-rate-limiter', '''flowchart LR
 C["Authenticated account request"] --> G["Gateway"] --> A["Atomic shared admission"]
 A --> Y["Allow"]
 A --> N["Reject with retry guidance"]
 A --> S[("Window or token state")]
 Y --> D["Protected dependency"]''', '''flowchart TD
 R["Identity, interval, burst, cost, scope"] --> A["Choose fixed, sliding, or token algorithm"]
 A --> C["Atomic check and record"] --> S[("Shared identity state")]
 C --> Y["Allow within the chosen contract"]
 C --> N["Reject; bounded client retry"]
 S --> F["Timeout or failover"] --> P["Endpoint-specific degraded policy"]
 R --> G["Global quota"] --> B["Disjoint regional budgets and fencing"]
 Y --> L["Concurrency and downstream saturation limits"]
 A --> V["Rule versions, metrics, and rollback"]''', 'Token-bucket bursts and exact rolling windows are different contracts.')

pair('06-consistent-hashing', '''flowchart LR
 K["Key hash"] --> R["Versioned ring or partition map"] --> O["Physical owner"]
 R --> V["Virtual positions distribute placement"]
 O --> P["Distinct replica failure domains"]''', '''flowchart TD
 R["Placement scheme and membership epoch"] --> K["Key to owner mapping"] --> O["Physical and failure-domain owners"]
 N["Add or remove owner"] --> M["Affected ownership interval"] --> C["Snapshot and concurrent-write catch-up"]
 C --> V["Verify and fence cutover"] --> R
 V --> B["Retain rollback window"]
 K --> H["Hot key or access skew"] --> S["Special serving, admission, or serialization policy"]
 O --> D["Replication and durability are separate protocols"]''', 'Balanced key placement does not prove balanced traffic or safe data migration.')

pair('07-key-value-store', '''flowchart LR
 C["Client"] --> O["Coordinator or fenced leader"]
 O --> A[("Replica A")]
 O --> B[("Replica B")]
 O --> D[("Replica C")]
 A --> R["Persisted acknowledgment under policy"]
 B --> R''', '''flowchart TD
 P["API and consistency contract"] --> K["Partitioned keys and owners"] --> L["Local durable write path"]
 L --> R["Replica acknowledgment and read policy"]
 R --> Q["R plus W greater than N: set overlap only"]
 Q --> V["Version selection, ordering, membership, durability"]
 R --> N["Partition or failed node"] --> S["Preserve authority or accept conflicts explicitly"]
 S --> C["Domain merge or conflict response"] --> A["Repair and convergence"]
 A --> R
 L --> B["Backup and verified restore"]
 P --> I["Conditional inventory needs a stronger atomic protocol"]''', 'Specify the complete read/write protocol before claiming a consistency guarantee.')

pair('08-notifications', '''flowchart LR
 O["Business action"] --> D[("Business row plus outbox in one transaction")]
 D --> P["Dispatcher"] --> Q["Queue"] --> W["Worker"] --> E["Provider"]
 W --> S[("Attempt and outcome state")]
 E -->|"timeout"| U["Unknown outcome; reconcile"]''', '''flowchart TD
 A["Accepted notification intent"] --> T["Atomic business and outbox commit"] --> Q["Durable dispatch; duplicates possible"]
 Q --> W["Lease work; check preferences and expiry"] --> R["Provider quota and retry budget"]
 R --> P["Send with stable provider identity when supported"]
 P --> K["Known result: record then acknowledge"]
 P --> U["Unknown result: reconcile or document trade-off"]
 R --> D["Backoff, jitter, dead-letter triage"]
 Q --> M["Queue age and completion latency"]
 M --> B["Admission or capacity when arrival exceeds service"]''', 'Durable local intent, broker delivery, and external effects have separate guarantee boundaries.')

pair('09-web-crawler', '''flowchart LR
 F[("Durable URL frontier")] --> H["Eligible host scheduler"] --> D["Bounded safe downloader"] --> P["Parse and fingerprint"] --> S[("Content and fetch state")]
 P --> N["Discovered links"] --> F''', '''flowchart TD
 S["Allowed sources and crawl budgets"] --> F["Durable discovered URL states"]
 F --> H["Host ownership, politeness, robots policy"] --> D["Resolve and validate destination and redirects"]
 D --> T["Fetch deadlines, body limits, bounded concurrency"] --> P["Persist and parse"]
 P --> C["Content fingerprints separate from URL identity"]
 P --> L["Deduplicated links and refresh schedule"] --> F
 T --> R["Failures: lease, fencing, backoff, replay"] --> F
 H --> M["Per-host limits survive adding workers"]''', 'Discovery, scheduling, fetching, and content identity are different stages.')

pair('10-news-feed', '''flowchart LR
 P["Author publishes"] --> D[("Canonical posts and durable event intent")]
 D --> F["Async fan-out"] --> V[("Viewer feed references")]
 R["Viewer reads"] --> V --> A["Resolve and authorize current content"] --> O["Ordered page"]''', '''flowchart TD
 R["Chronological or ranked? Freshness and privacy?"] --> P[("Canonical post and access policy")]
 P --> F["Push ordinary authors; pull high fan-out authors"] --> V["Idempotent derived feed references"]
 V --> C["Merge by defined ordering and cursor"] --> A["Current access and deletion checks"] --> O["Visible page"]
 P --> D["Revocation freshness distinct from feed lag"] --> A
 F --> H["Celebrity and active-follower amplification"] --> M["Lag, capacity, rebuild and replay"]
 M --> V''', 'A stale projection can be acceptable for freshness while still being unsafe for authorization.')

pair('11-chat', '''sequenceDiagram
 participant S as Sender
 participant A as Message service
 participant D as Durable history
 participant R as Recipient
 S->>A: Message plus stable request ID
 A->>D: Authorized ordered append
 D-->>A: Durable commit
 A-->>S: Accepted
 A->>R: Live delivery attempt
 R-->>A: Device acknowledgment
 R->>A: Reconnect after cursor
 A->>D: Fetch missing history''', '''flowchart TD
 S["Sender identity and membership"] --> I["Stable request deduplication"] --> D[("Durable per-conversation history")]
 D --> A["Accepted acknowledgment"]
 D --> W["Delivery through current gateway"] --> R["Recipient device receipt"]
 R --> C["Catch-up cursor and offline replay"] --> D
 G["Soft connection registry"] --> W
 P["Heartbeat expiry"] --> O["Approximate presence"]
 G --> B["Bounded buffers and reconnection control"]
 D --> V["Protocol versions, retention, and access checks"]''', 'Accepted, delivered, and read are distinct states; live transport does not replace history.')

pair('12-autocomplete', '''flowchart LR
 E["Eligible query events"] --> A["Aggregate and rank"] --> B["Build verified index version"] --> I[("Published prefix index")]
 P["Prefix request"] --> I --> F["Policy filter"] --> T["Top-K suggestions"]''', '''flowchart TD
 C["Matching, language, privacy, freshness"] --> D["Eligible data and normalization"] --> A["Aggregate scores"]
 A --> B["Build immutable prefix and top-K index"] --> V["Validate and publish version"]
 P["Prefix lookup"] --> V --> T["Fast allowed results"]
 R["Urgent blocked-term policy"] --> T
 T --> O["Match response to current client input"]
 C --> K["Tenant-aware index and cache keys"] --> P
 V --> F["Rollback, index age, and hot-prefix serving"]''', 'Build-time freshness, emergency removal, and out-of-order UI responses need separate mechanisms.')

pair('13-video-platform', '''flowchart LR
 U["Authorized upload session"] --> S[("Verified source object")]
 S --> P["Processing DAG"] --> R[("Immutable renditions")]
 R --> M["Publish ready manifest"] --> C["Authorized CDN playback"]''', '''flowchart TD
 A["Owner and tenant authorization"] --> U["Resumable scoped upload"] --> S["Verify source completion"]
 S --> J["Durable job and output identity"] --> D["Probe, transcode, thumbnails, package"]
 D --> V["Verify required outputs"] --> M["Atomic ready manifest publication"]
 M --> C["Access-aware CDN and segment serving"] --> P["Adaptive playback"]
 P --> E["Viewers times bitrate: egress and cost"]
 J --> R["Retry immutable outputs; clean abandoned work"]
 C --> F["Origin fallback, privacy, and deletion policy"]
 P --> O["Startup delay and rebuffering SLI"]''', 'The control plane manages ownership/status; the data plane moves large media bytes.')

pair('14-file-sync', '''sequenceDiagram
 participant C as Device
 participant O as Object storage
 participant M as Metadata service
 participant L as Change log
 C->>O: Resumable immutable content upload
 O-->>C: Verified content reference
 C->>M: Commit with expected base version and operation ID
 M->>L: Atomic metadata and durable change
 M-->>C: New version or conflict
 C->>L: Catch up after cursor''', '''flowchart TD
 F["Stable file identity and access"] --> U["Upload session and verified immutable chunks"]
 U --> C["Conditional metadata publication against base version"]
 C --> V["Commit and durable change log"] --> D["Device cursor catch-up"]
 C --> X["Conflict: preserve copy or explicit merge"]
 T["Versioned delete and rename metadata"] --> C
 O["Offline old editor"] --> C
 V --> G["Retained-version references and safe garbage collection"]
 D --> R["Expired cursor: snapshot resync"]
 F --> A["Tenant-scoped permissions and private dedup policy"]''', 'Uploading bytes and publishing a new visible version are separate state transitions.')

pair('15-production-architecture', '''flowchart LR
 C["Useful user contract"] --> S["SLI and SLO"] --> M["Evidence and failure hypothesis"] --> D["Decision with alternatives"] --> R["Canary rollout"] --> V["Verify or rollback"]''', '''flowchart TD
 U["User-visible success and error budget"] --> O["Observe latency, correctness, backlog"]
 O --> F["Bound failures: deadlines, retries, admission, bulkheads"]
 F --> B["Recovery: RPO, RTO, tested restore"]
 T["Assets and trust boundaries"] --> A["Resource and tenant authorization"]
 E["Change proposal"] --> X["Expand compatible representation"] --> M["Migrate and reconcile"] --> C["Canary cutover"] --> K["Contract old representation later"]
 C --> R["Valid rollback and evidence"]
 U --> P["Cost drivers and measured capacity"]
 A --> E''', 'A production design includes observed service behavior, recoverability, and safe change.')

pair('16-final-assessment', '''flowchart LR
 P["Unfamiliar prompt"] --> A["Unaided 45-minute attempt"] --> C["Changed constraint"] --> E["Rubric evidence"] --> R["Repair and delayed transfer"]''', '''flowchart TD
 F["Framework retrieved from memory"] --> A["Read-heavy transfer round"]
 F --> B["Async transfer round"]
 F --> C["Correctness transfer round"]
 A --> S["Eight dimensions and specific evidence"]
 B --> S
 C --> S
 S --> I{"Invariant intact and unaided adaptation?"}
 I -->|"no"| R["Repair one mechanism and reattempt"] --> S
 I -->|"yes"| P["Passing evidence in at least two rounds"]
 P --> W["Real-system review: facts, inference, proposal"] --> M["Maintenance and later retrieval"]''', 'Graduation is measured by independent transfer and evidence, not by chapter counts.')
