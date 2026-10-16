"""Original teaching material mapped to the thirteen Volume 2 chapters.

Book references use printed page numbers; the scan has irregular PDF offsets.
No book images or text are redistributed. Edit this source, then run build_hld_course.py.
"""
from copy import deepcopy
import re

MODULES = []
PHASES = ['Contract', 'Size', 'Model', 'Flow', 'Stress', 'Operate', 'Explain']


def add(slug, title, chapter, pages, hours, prerequisites, rows, details, teaching, phases,
        practice, transfer, transfer_answer, repair, repair_answer, quiz, diagram, recap, lab=None):
    number = 17 + len(MODULES)
    sections = []
    for i, (row, detail) in enumerate(zip(rows, details)):
        heading, explanation, example, tip = row
        sections.append({'id': f'section-{i}', 'title': heading, 'quick': dict(title=heading, explanation=explanation, example=example, tip=tip),
                         'content': detail})
    recall = f'Without notes, explain {title.lower()}. Trace one request, one retry or race, and one failure. Which requirement would change your design?'
    sections.append({'id': f'section-{len(rows)}', 'title': 'Retell the whole design', 'quick': {
        'title': 'Close the lesson. Tell the story.', 'explanation': 'Use the recap picture to explain the design aloud. Then hide it and try again.',
        'example': recap[-1], 'tip': 'Promise → path → failure → repair.'}, 'content': recall})
    solution = '\n\n'.join(f'### {name}\n{text}' for name, text in zip(PHASES, phases))
    # A separate, small teaching case demonstrates the framework before the unseen practice variants.
    examples = [{'id': 'example-0', 'title': 'Follow a small worked example', 'content': teaching}]
    questions = []
    for i, (prompt, correct, wrong1, wrong2, wrong3, explanation) in enumerate(quiz):
        options = [wrong1, wrong2, wrong3]
        correct_index = (i + chapter) % 4
        options.insert(correct_index, correct)
        questions.append(dict(id=f'q{i+1}', prompt=prompt, options=options, correctIndex=correct_index, explanation=explanation))
    recap_code = 'flowchart TD\n' + '\n'.join(f'  R{i}["{label}"]' for i, label in enumerate(recap)) + '\n' + '\n'.join(f'  R{i} --> R{i+1}' for i in range(len(recap)-1))
    MODULES.append(dict(id=slug, number=number, track='volume-2', chapter=chapter, title=title, hours=hours,
                        prerequisites=prerequisites, book=f'Volume 2, chapter {chapter}; printed pages {pages}.',
                        outcome=rows[0][1], sections=sections, examples=examples, recallPrompt=recall,
                        lab=lab, visuals=[dict(id='overview', title='Follow the main path', caption='An original diagram. Follow the arrows before adding more boxes.', placement='overview', code=diagram),
                                          dict(id='recap', title='The whole idea, in one picture', caption='Hide this picture. Rebuild the explanation from memory.', placement='recap', code=recap_code)],
                        exercises=[dict(id='p1',title=practice[0],kind='design',minutes=45,prompt=practice[1],solution=solution),
                                   dict(id='p2',title=transfer[0],kind='transfer',minutes=30,prompt=transfer[1],solution=transfer_answer),
                                   dict(id='p3',title=repair[0],kind='repair',minutes=20,prompt=repair[1],solution=repair_answer)], questions=questions))


add('17-proximity', 'Find nearby places', 1, '1–34', 4, '01 scale; 02 data and caches', [
('Search a small area first', 'A nearby search should inspect a small part of the map. First find possible matches. Then check the real distance.', 'A cafe across a grid border may be closer than one inside your own cell.', 'Cells find candidates. Distance picks matches.'),
('Choose a spatial index', 'A geohash labels a grid cell. A quadtree splits crowded areas into smaller boxes. Both help skip far-away places.', 'A busy city needs smaller cells than an empty field.', 'Choose the index from density and update rate.'),
('Keep place data separate', 'The place database owns names and opening hours. The location index helps find IDs. It can be rebuilt from the database.', 'Changing a cafe name should not require rebuilding the world map.', 'Source data first. Search view second.'),
('Check borders and stale results', 'Search all cells that overlap the requested circle. Filter by actual distance and current visibility. Define how quickly a closed place disappears.', 'Deleting a shop in the database does not instantly remove a cached search result.', 'A fast candidate list still needs a final check.'),
('Size and operate the search', 'Count searches per second and candidates per search. Watch dense cells, response time, and the age of index updates.', 'One airport cell can attract far more searches than a rural cell.', 'Measure the busiest cell, not only the average.')], [
'For a radius query, a bounding box or cell cover narrows the search. Exact geographic distance removes false matches. Choose how to handle an empty result and whether the product may expand the radius. A nearest-K query is a different contract from returning everything inside a radius.',
'Geohash prefixes give convenient buckets, but sharing a prefix does not prove two points are the closest pair. Include neighboring/intersecting cells. A quadtree adapts to density but needs tree management. A database spatial index is a sensible first implementation; explain why custom distributed indexing is needed before adding it.',
'Use place_id as the stable identity. Store latitude, longitude, owner, visibility, and an update version. Search returns candidate IDs, then batch-loads details. An outbox or change stream updates the index. Duplicate or out-of-order updates must not restore an older version.',
'Cell selection must cover the whole search circle, including edge cases near the date line. Exact filtering removes candidates outside the radius. For urgent removal, a final authoritative visibility check or fast deny list can enforce the stronger rule while the index catches up.',
'Cache popular coarse searches only under an explicit freshness budget. Do not cache a separate response for every precise coordinate. Track candidates inspected, p95 latency, hot-cell traffic, update lag, and removal failures. Precise user coordinates are sensitive; bound retention and access.'
], '''### Contract
Find open cafes within 1 km. Updates may lag one minute. Do not promise nearest driving time.
### Size
At 100 searches/s and 200 candidates/search, the distance stage handles about 20,000 checks/s. This is the estimate that matters first.
### Model
Keep Cafe(id, point, visible, version) in the source database. Index point → cafe IDs.
### Flow
Cover the circle with cells → fetch candidate IDs → check distance and visibility → sort and return.
### Stress
Pause here: a cafe sits just across a cell edge. Which lookup would miss it?

Searching only the user's cell misses it. Include intersecting cells and remove false matches by distance.
### Operate
Measure search latency and index lag. Remove precise coordinates from ordinary logs.
### Explain
A database spatial index may be enough at this scale. A distributed cell index adds capacity but also update and border handling.''', [
'Find visible places within 5 km. Define result limit, sorting, one-minute update lag, and an immediate owner-removal rule. Straight-line distance is sufficient.',
'Assume 20 million places and 5,000 searches/s, peak 15,000. At 300 candidates/search, peak filtering is 4.5 million candidates/s; benchmark density skew before sharding. State bytes per place and cache hit assumptions.',
'GET /places?lat=&lon=&radius=&cursor=. Place(id, point, details, visible, version) is authoritative. A spatial index and optional coarse-cell cache are derived. Use a stable tie-breaker for pagination.',
'Cover the query circle, read candidate IDs, batch-fetch details, filter distance and visibility, then rank. Owner updates commit source plus change event together. Version-aware index consumers replay safely.',
'Test a cell boundary, dense city, removed place still cached, and out-of-order index event. Immediate removal needs an authoritative deny/visibility check; the one-minute search freshness budget alone cannot satisfy it.',
'Observe candidate count, hot cells, cache hit rate, latency, and update lag. Rebuild a versioned index alongside the old one, compare results, switch gradually, and retain rollback. Bound coordinate retention.',
'A spatial database minimizes moving parts. A cell index supports independent serving scale but needs border coverage and replay. More precise cells reduce candidates while increasing fan-out and cache fragmentation.'
], ('Nearby repair shops', 'Design repair-shop search for 20 million places and 5,000 searches/s, peaking at 15,000. Return at most 50 visible shops within 5 km. Ordinary updates may lag one minute; owner removal must apply immediately. Cover indexing, borders, updates, and hot areas.'),
('Walking time replaces distance', 'Now return places reachable within ten minutes on foot. Explain what changes and why a circle is insufficient.'),
'A circle can generate initial candidates, but walking reachability needs a routable graph with crossings, access rules, and path costs. Use a conservative candidate region, then route/rank with travel-time costs. State approximation and compute budgets. Rivers and restricted roads make straight-line order wrong. Reuse the place source and versioned updates; monitor route-service latency separately.',
('A missing cafe', 'Bad design: hash the user coordinate, read only that exact cell, and return every place ID from it. Name two wrong results and repair the read path.'),
'A nearby cafe across the border is missed; a far corner in the same cell can be outside the requested radius. Cover every cell intersecting the query circle, then check true distance. Recheck current visibility. Test points exactly on boundaries and just inside/outside the radius.', [
('A shop is across the cell border but 10 m away. What must the query do?', 'Search intersecting cells, then filter distance.', 'Read only the same cell.', 'Increase every cell to city size.', 'Trust prefix equality as distance.', 'Cell boundaries are index boundaries, not product distance rules.'),
('What should own a shop name?', 'The place source database.', 'Every cached radius response independently.', 'Only the geohash string.', 'The browser session.', 'The index is a rebuildable view of stable place records.'),
('Which estimate exposes dense-area cost?', 'Candidates inspected per search at peak load.', 'Only total registered users.', 'Only the number of API methods.', 'The length of a place name.', 'Candidate count multiplied by search rate estimates filtering work.'),
('A removed place remains in a cached candidate list. What enforces immediate removal?', 'A current authoritative visibility check or fast deny path.', 'A one-day cache expiry.', 'A longer geohash.', 'Randomly dropping results.', 'Freshness of a derived view alone cannot promise immediate removal.')],
'''flowchart TD
  U["User: point and radius"] --> C["Cover circle with cells"]
  C --> I["Spatial index: candidate IDs"]
  I --> D["Place database: details and visibility"]
  D --> F["Exact distance and access check"]
  F --> R["Sort and return places"]
  W["Owner update"] --> D
  D --> E["Versioned change events"]
  E --> I''', ['Define radius and freshness', 'Cover the full circle', 'Fetch candidate place IDs', 'Check distance and visibility', 'Rank and return', 'What if a place sits across a cell border?'], lab='geo')

add('18-nearby-friends', 'Track nearby friends safely', 2, '35–58', 4, '17 proximity; 11 chat', [
('Moving people change the problem', 'Places rarely move. People move all the time. Separate the latest location from the list of people allowed to see it.', 'A friend sends a new location every ten seconds. Last week’s position is not useful.', 'Location needs a timestamp and an expiry.'),
('Route live updates', 'A connection server keeps a live link to the phone. A location service records a versioned update and tells interested watchers.', 'A reconnect may land on a different server. The old connection must not own the new session.', 'A socket is a route, not the source of truth.'),
('Limit who watches whom', 'Use the friendship graph and nearby cells to limit updates. Subscribe only to relevant people or areas.', 'Sending every movement to a million users creates huge fan-out.', 'Filter interest before sending updates.'),
('Treat privacy as part of the flow', 'Check permission when a watcher subscribes and when an update is sent. Old subscriptions must not keep working after permission is removed.', 'A blocked friend should stop receiving location even if their socket stays connected.', 'Revoking access must reach live subscriptions.'),
('Handle stale and late updates', 'Discard an older location version. Expire silent users. Label a location stale rather than pretending it is current.', 'A delayed packet from before a train ride must not move the user backwards.', 'New arrival does not always mean new location.')], [
'Define distance, expected refresh interval, offline behavior, and visibility controls before choosing transport. Distinguish precise coordinates, approximate presence, and the claim that a friend is currently nearby. Their retention and freshness requirements differ.',
'WebSocket gateways maintain session routes. A location record carries user_id, session/version, point, received_at, and expiry. Server-issued sequence/session epochs can reject packets from obsolete sessions. Do not blindly trust phone clocks or allow one user to publish another user’s position.',
'A pub/sub layer can route relevant updates to gateways with interested clients. Use friend relationships first and spatial grouping when needed. Subscription churn and hot areas are costs. Coarse cells narrow candidates; the final distance check decides actual proximity.',
'Authenticate the publisher and watcher. A permission version, subscription invalidation, or send-time check must enforce a stated revocation deadline. A database update followed by asynchronous cache expiry cannot silently claim instant revocation. Avoid retaining precise trails unless needed.',
'Choose behavior for disconnection and packet reordering. Expiry helps hide old presence but is not a guarantee of deletion from every derived store. Observe end-to-end update age, subscription fan-out, blocked-send failures, and gateway reconnect storms.'
], '''### Contract
Show two friends approximately nearby. Updates refresh every ten seconds. Stop sharing within two seconds of blocking.
### Size
100,000 online users / 10 seconds = 10,000 inbound updates/s. Outbound load also depends on active watchers.
### Model
Location(user, session_epoch, sequence, point, expires_at) plus a separate permission record.
### Flow
Phone → authenticated gateway → version check → latest location → allowed watchers → their gateways.
### Stress
Predict: what if an old socket publishes after a reconnect?

Reject its obsolete session epoch. A new TCP connection alone does not invalidate old application messages.
### Operate
Track update age and revocation delay. Expire silent locations.
### Explain
WebSocket gives timely transport. It does not prove freshness, permission, or ordering by itself.''', [
'Nearby friends within 2 km; 10-second updates; stale locations hidden after 30 seconds; permission revocation effective within two seconds. Define approximate distance and offline behavior.',
'One million online users / 10 seconds = 100,000 updates/s before bursts. If each has five active watchers, roughly 500,000 outbound updates/s. Bound watchers and measure skew.',
'Location(user_id, session_epoch, sequence, point, received_at, expires_at); Friendship and SharingPolicy as authority. Gateway routing is ephemeral. Authenticate both sides and never trust client-supplied owner identity.',
'Accept an authenticated location only if its session/version is current. Store latest state with expiry, find eligible nearby watchers, check permissions, publish to their gateways. Reconnect resubscribes from current allowed state.',
'Test reordered updates, duplicate packets, old sessions, and a block during delivery. Invalidate subscriptions and enforce a send-time policy/version check within the two-second budget. Treat uncertain/expired data as unavailable.',
'Measure update age, revocation delay, fan-out, active subscriptions, and reconnect rate. Rate-limit publishers and avoid location trails in logs. Rebuild routing after gateway loss without reviving expired locations.',
'Per-user subscriptions are simple for small friend lists; area channels may reduce routing overhead in dense regions but need strict filtering. Precision and retention increase privacy cost.'
], ('Friends at a festival', 'Design nearby friends for one million online users. Phones update every ten seconds. Show friends within 2 km; hide positions older than 30 seconds. Blocking must stop sharing within two seconds. Cover session changes, permission checks, and overloaded festival cells.'),
('Battery-saving mode', 'Phones may now update only once per minute. The UI still asks for nearby friends. What promise must change?'),
'Keep the server receipt time and display last-updated age. With one-minute sampling you cannot honestly promise a ten-second location. Use approximate/stale labels, a wider uncertainty region, or request an explicit refresh with user consent. Preserve revocation checks independently of location sampling. Explain the battery, precision, and freshness trade-off.',
('Old subscriptions leak', 'Bad design: permission is checked only when a WebSocket opens. Blocking updates the database but does not touch subscriptions. Repair it.'),
'Apply permission checks to subscriptions and deliveries. Publish a policy-version invalidation and remove live watchers; enforce the two-second deadline with a bounded refresh or authoritative send gate. Test an already connected blocked watcher and an event queued before the block. Hide old cached locations from newly unauthorized queries.', [
('Which record prevents a delayed old session from replacing a new location?', 'A current session epoch and sequence.', 'Only packet arrival order.', 'The friend’s display name.', 'The gateway hostname alone.', 'Application versions reject obsolete sessions and older updates.'),
('Why is inbound update rate not the full capacity estimate?', 'Each update may fan out to many watchers.', 'WebSockets remove all outbound work.', 'Friend lists never change.', 'Expiry eliminates network traffic.', 'Outbound work is update rate multiplied by relevant active watchers.'),
('A phone last updated 90 seconds ago. What should the app do?', 'Hide or clearly mark it stale under the agreed contract.', 'Call the last point current.', 'Move it to the cell center.', 'Invent a likely position.', 'A last-known point does not establish a current location.'),
('What must a block operation affect?', 'Live delivery permission as well as stored friendship state.', 'Only the next app installation.', 'Only the map color.', 'Only inbound location writes.', 'Already established subscriptions can otherwise keep leaking location.')],
'''flowchart TD
  P["Phone location and version"] --> G["Authenticated live gateway"]
  G --> L["Latest location with expiry"]
  L --> S["Find relevant watchers"]
  A["Sharing permissions"] --> S
  S --> V["Check permission before send"]
  V --> W["Watcher gateways"]
  W --> F["Friends: fresh or stale status"]
  A --> V''', ['Promise freshness and revocation', 'Accept only the current session', 'Store latest location with expiry', 'Find relevant allowed watchers', 'Send and expire stale state', 'What if a block happens during delivery?'])

add('19-maps', 'Build maps and route guidance', 3, '59–90', 5, '17 proximity; 13 video delivery', [
('Separate maps from routes', 'A map image and a route answer solve different problems. Serve reusable map tiles through a CDN. Compute routes from a road graph.', 'Ten users can share the same map tile but need ten different routes.', 'Tiles are pictures. Routes are paths.'),
('Model roads as a graph', 'Junctions are points. Road segments connect them. Segment cost can include travel time, direction, and turn restrictions.', 'The shortest line may cross a river with no bridge.', 'Distance alone is not a driving route.'),
('Version the map data', 'Build tiles and route graphs from a known map version. Publish new versions safely. Keep a rollback path.', 'A closed road must not stay open in the graph after the map update.', 'Know which map version answered.'),
('Add live traffic carefully', 'Traffic changes route costs. Keep base roads separate from recent traffic estimates. Label old traffic data.', 'An old congestion sample should not overwrite a newer road-speed estimate.', 'Stable graph. Changing costs.'),
('Keep navigation useful on failure', 'Cache the current route on the phone. Reroute when needed. Batch location telemetry and keep it private.', 'Losing signal in a tunnel should not erase the next turn.', 'A route already delivered should survive a brief outage.')], [
'Clarify map viewing, route search, and turn-by-turn navigation. A viewport requests tiles by zoom/x/y. Tile traffic is highly cacheable and bandwidth-heavy. Personalized route traffic depends on origin, destination, mode, restrictions, and current graph version.',
'Route search uses directed edges, turn restrictions, and travel-time weights. Dijkstra/A* are starting points; large road graphs often need hierarchical preprocessing. State approximation and update trade-offs instead of promising a planet-wide graph scan per request.',
'An offline pipeline validates road changes and builds versioned graph partitions and tiles. Publish a manifest, canary route results, and retain the previous version. Graph seams and cross-region trips need connected boundary nodes.',
'Live probes need sampling, privacy controls, map matching, outlier handling, and freshness. Aggregate speeds by road segment and time window. A cost change may invalidate a cached route even when road geometry is unchanged.',
'Track tile hit rate, route latency, route failures, traffic age, reroute frequency, and version mismatch. If traffic ingestion fails, fall back to historical travel time with an honest indication. Do not make navigation depend on uploading each location synchronously.'
], '''### Contract
A campus shuttle app shows a map and routes along allowed roads. Live traffic is optional.
### Size
100 tiles per view × 100 views/s = 10,000 tile requests/s before caching. Route requests are a separate smaller workload.
### Model
Versioned tiles and directed road edges with travel-time costs.
### Flow
Fetch tiles from CDN. Send origin/destination to route service. Store returned turns on the phone.
### Stress
Predict: the phone loses signal after getting a route. Must it stop showing turns?

No. Keep route geometry and turns locally; mark traffic updates unavailable.
### Operate
Watch failed routes and graph versions. Compare sample trips before switching graphs.
### Explain
Serving tiles cheaply does not solve route computation. Each path needs its own capacity and failure plan.''', [
'Support map browsing and car routes for one country. p95 route latency target two seconds; traffic may lag two minutes. Keep last route available offline. Exclude transit schedules and street-view imagery.',
'At 50,000 map views/min and 40 tiles/view, about 33,333 tile requests/s before CDN hits. If 10% request a route, about 83 route requests/s. Peaks and reroute storms need separate headroom.',
'Tiles keyed by map_version/zoom/x/y. Road graph has directed segments, geometry, restrictions, and costs. Route API accepts origin, destination, mode, and avoid rules; returns versioned geometry and turns.',
'Build and publish validated versioned graph/tiles. CDN serves tiles. Route service snaps endpoints to roads, searches with travel-time costs, and returns steps. Traffic ingestion updates recent costs. Client stores route for brief outages.',
'Test disconnected graph components, a one-way road, closed bridge, stale traffic, and a regional graph boundary. Reroute conservatively; if traffic is stale, use historical costs and label the estimate.',
'Observe route latency, no-route rate, tile cache hits, traffic age, and graph version. Canary known trips, compare distances/times, switch manifests gradually, and retain rollback. Minimize precise-location logs.',
'A global graph is simpler conceptually but expensive to search and update. Hierarchical graphs speed long trips at preprocessing cost. Tiles use CDN capacity; routing uses compute. Do not size them as one workload.'
], ('A country-wide driving app', 'Design map browsing and car routes. Expect 50,000 map views/minute, 40 tiles/view, and route searches from 10% of views. Target p95 route latency under two seconds. Traffic may lag two minutes. Keep current directions usable during a network outage.'),
('A bridge closes now', 'A bridge closes immediately after graph version publication. How do you stop new routes using it without rebuilding all tiles?'),
'Apply a versioned road-closure overlay checked by route search and route-cache validation. Invalidate affected active routes and suggest rerouting. Tile imagery may update later; routing safety rules must use the newer closure data. Preserve expiry, authority, and rollback of overrides. Track closure-to-route enforcement delay.',
('One cache for everything', 'Bad design: cache every route for one day keyed only by origin and destination. Repair the key and invalidation rules.'),
'Include travel mode, avoid rules, graph version, and an appropriate origin/destination normalization. Traffic-aware routes need a bounded time bucket or dependency invalidation; emergency closures require a current closure check. Private user options must not leak through shared cache entries. A one-day TTL cannot honor two-minute traffic freshness.', [
('What is a map tile best served through?', 'A versioned object path and CDN.', 'A fresh shortest-path search per pixel.', 'The payment database.', 'A user-specific queue for each pixel.', 'Tiles are reusable content; routing is a different request path.'),
('Why model roads as directed edges?', 'One-way roads and allowed travel directions matter.', 'Every road can always be used both ways.', 'Direction only changes the tile color.', 'It removes the need for costs.', 'Road connectivity and direction constrain valid routes.'),
('Traffic ingestion stops. What is an honest fallback?', 'Historical costs with a stale-traffic indication.', 'Claim every route has live traffic.', 'Delete all roads.', 'Wait forever before returning any route.', 'Base geometry can still support useful routes with weaker time estimates.'),
('What must an emergency closure affect first?', 'Route eligibility, including cached routes.', 'Only the next image-tile rebuild.', 'Only app theme settings.', 'Only the location upload interval.', 'Tiles can lag while route decisions enforce current closures.')],
'''flowchart TD
  P["Phone"] --> T["CDN: versioned map tiles"]
  P --> R["Route API"]
  R --> G["Road graph and restrictions"]
  C["Traffic and closure updates"] --> G
  G --> S["Search path and build turns"]
  S --> O["Phone stores route for outages"]
  M["Map build pipeline"] --> T
  M --> G''', ['Separate tiles from route search', 'Version roads and restrictions', 'Add fresh traffic costs', 'Compute and deliver turns', 'Keep route through short outages', 'What if a bridge closes after publication?'])

add('20-message-queue', 'Build a durable message queue', 4, '91–130', 5, '07 key-value store; 08 async workflows', [
('A queue owns a promise', 'Define when a producer may believe a message is safe. Also define how long consumers can replay it.', 'A message only in one machine’s memory can vanish after that machine fails.', 'Accepted must have a durability boundary.'),
('Partition the log', 'A partition is an ordered list with numbered positions. Different partitions run in parallel. Order is local to each partition.', 'All updates for one order use the same key. Two unrelated orders can use different partitions.', 'More partitions give parallelism, not global order.'),
('Replicate before the right reply', 'A leader accepts writes. Followers copy them. The reply rule and safe leader election together decide what survives a failure.', 'A follower that missed acknowledged data must not become leader and silently lose it.', 'A safe reply needs a safe next leader.'),
('Separate work from progress', 'A consumer offset says how far a group has processed. Saving it too early loses work. Saving it after work can cause repeats.', 'A worker updates a database, crashes before saving its offset, then sees the same message again.', 'Replay-safe effects make retries useful.'),
('Bound backlog and recover', 'Retention is finite. Watch the oldest unread message and consumer lag. A growing queue cannot fix a permanently slow worker.', 'If arrivals are 300/s and workers handle 200/s, backlog grows 100/s.', 'A buffer buys time, not infinite capacity.')], [
'Choose retained pub/sub or a task queue explicitly. This module builds a retained partitioned log with independent consumer groups. A producer acknowledgment refers to the configured replicated commit boundary. A consumer acknowledgment means group progress, not that every external effect happened exactly once.',
'Append messages with partition offsets. The partition key keeps related events together. Consumer-group assignments grant one active owner per partition within that group; ownership epochs fence stale workers during rebalance. Changing partition count may change key placement and ordering, so plan migration.',
'Replication, minimum eligible replicas, producer acknowledgment policy, and election eligibility are one design. Refuse unsafe writes/elections when the contract requires no acknowledged-message loss. Disks and replication do not prevent all losses: define the supported failure model and recovery point.',
'Commit the business effect and deduplication record in one local transaction where possible. Then advance the consumer position. A crash between them repeats delivery but the effect remains safe. Broker transactions have a scope; an arbitrary external email or payment service is not automatically included.',
'Capacity includes ingress bytes, replicated bytes, retention storage, and consumer read traffic. Segment files support sequential I/O and retention deletion. Track per-partition lag age, disk headroom, replication health, and rebalance rate. Consumers behind retention need snapshot recovery or a documented data-loss response.'
], '''### Contract
Store order events for two days. Billing and analytics read independently. Keep order-local sequence.
### Size
1,000 messages/s × 1 KB × 172,800 s ≈ 173 GB raw. Three copies need about 518 GB before indexes and headroom.
### Model
Topic → partition → offset. Each consumer group has its own progress.
### Flow
Key by order ID → append → replicate to the commit rule → reply. Consumers process and then commit offsets.
### Stress
Predict: billing saves an invoice and crashes before the offset commit.

The message returns. A unique order/event identity prevents a second invoice in the same database transaction.
### Operate
Watch oldest unread age and disk space, not only message count.
### Explain
Partition order is enough for one order. Global order would restrict parallelism without helping this contract.''', [
'Retained pub/sub log, order-local ordering, independent consumer groups, seven-day replay, at-least-once delivery. No acknowledged-message loss for one replica failure under the chosen commit/election rules.',
'20,000 messages/s × 1 KB = 20 MB/s ingress. Seven days ≈12.1 TB raw decimal, about36.3 TB at three copies before overhead. Include read fan-out, bursts, and headroom.',
'Topic metadata maps partitions to leaders/replicas and epochs. Message carries key, event_id, payload, checksum. Offset is partition-local. Group offsets and assignments are durable control metadata.',
'Producer resolves leader, appends by key, waits for the supported replicated commit boundary, and retries with stable identity if uncertain. Consumer processes durably, records deduplication with local effect, then commits offset.',
'Crash a leader before and after acknowledgment. Elect only a sufficiently caught-up replica. Fence old leaders/workers. A consumer crash after effect but before offset replays safely. A gap older than retention needs recovery rather than pretend replay.',
'Measure lag age, disk headroom, replication lag, rejected writes, and rebalance duration. Rotate/delete segments under retention. Throttle tenants and test restore. Queue age and bytes need alerts.',
'Partitions increase throughput but limit ordering scope. Waiting for safer replication raises latency and can reduce availability. A broker alone cannot make unrelated external effects exactly once.'
], ('A seven-day event log', 'Design a retained message queue for 20,000 messages/s of 1 KB each. Keep seven days. Billing and analytics consume independently. Preserve order per order ID. Survive one replica failure without losing acknowledged messages. Explain consumer crash recovery and storage needs.'),
('A slow consumer misses retention', 'Analytics is offline for ten days, but retention is seven. Design recovery without claiming all events can still be replayed.'),
'Detect the offset falling behind the retained beginning. Stop normal consumption and recover from a trusted snapshot plus retained tail, or an archive if one was deliberately kept. State any unrecoverable gap. Version the snapshot and align it to partition positions. Raising retention now cannot recreate deleted events.',
('Offset committed too soon', 'Bad consumer: save offset; charge customer; if it crashes, restart from saved offset. Repair the order and the external effect boundary.'),
'Saving the offset first can skip a charge. Process with a durable operation identity, provider idempotency/status lookup, and local state transitions; commit the offset after durable handling. A crash can replay the message, so retries reuse the identity. Reconcile unknown provider results. Moving the offset line alone does not make the remote charge atomic.', [
('What order does a partitioned log naturally provide?', 'Order within a partition.', 'One universal order across all topics.', 'Wall-clock order across every region.', 'No need to choose a message key.', 'Partition-local positions do not define an order between different partitions.'),
('A consumer crashes after saving its effect but before saving progress. What helps?', 'Replay with a durable deduplication identity tied to the effect.', 'Always commit progress before work.', 'Delete every retry.', 'Assume network delivery is unique.', 'Delivery can repeat; the effect must handle that repeat.'),
('Arrivals are 300/s and service is 200/s. What happens?', 'Backlog grows by about 100/s.', 'The queue automatically catches up.', 'Backlog shrinks by 100/s.', 'Replication eliminates the overload.', 'A buffer cannot repair sustained arrival rate above service capacity.'),
('What must accompany a strong producer acknowledgment?', 'Election rules that reject a successor missing committed data.', 'Electing any reachable replica.', 'Only a large memory cache.', 'Deleting group offsets.', 'A safe acknowledgment can still be undone by an unsafe leader election.')],
'''flowchart TD
  P["Producer and stable message ID"] --> L["Partition leader: append"]
  L --> R["Followers replicate"]
  R --> A["Commit boundary then acknowledge"]
  L --> C["Consumer group reads offsets"]
  C --> E["Durable replay-safe effect"]
  E --> O["Commit group progress"]
  O --> C''', ['Define retention and acknowledgment', 'Key messages into ordered partitions', 'Replicate and fence old leaders', 'Process with replay-safe effects', 'Save progress and watch lag age', 'What if a worker crashes after its effect?'], lab='queue')

add('21-metrics-alerting', 'Measure systems and send useful alerts', 5, '131–158', 4, '08 async; 15 production architecture', [
('Start from a user problem', 'Choose signals that show whether users can finish their task. Add machine signals to explain failures.', 'CPU can be low while every checkout request fails.', 'Measure the symptom before the cause.'),
('A metric is a series', 'A metric name plus labels identifies a time series. Every new label combination adds storage and work.', 'region=west is bounded. user_id can create millions of series.', 'Labels multiply.'),
('Collect and store in stages', 'Collectors buffer samples. Ingestion validates them. A time-series store serves time-range queries and rollups.', 'A short collector outage should not block the application request.', 'Monitoring must not become the outage.'),
('Alerts need state', 'Evaluate a rule over time. Group related failures and remember when an alert opens or resolves.', 'One noisy service should not send a thousand separate pages.', 'Detect → group → notify → resolve.'),
('Test the monitor itself', 'Missing samples can mean the collector died. Track data freshness and test the notification path too.', 'A quiet dashboard may be healthy or disconnected.', 'No data is a state, not automatically success.')], [
'Use latency, traffic, errors, and saturation to cover service symptoms and capacity. Define the objective and which request population counts. An alert should point to a useful action; dashboards can carry lower-urgency information.',
'A series is identified by metric name and complete label set. 100 services ×20 instances ×5 status classes already gives10,000 possible series. Unbounded request IDs or user IDs can explode memory/index size. Logs/traces are often better for individual-request detail.',
'Choose push or pull from deployment and discovery needs. Buffer with a bounded disk queue and a deliberate drop policy. Validate types, timestamps, and allowed labels. Write recent data at fine resolution, then roll up older windows while retaining enough detail for the actual questions.',
'Rule evaluation needs pending/firing/resolved states, a duration threshold, grouping, deduplication, and delivery retries. An alert fingerprint makes retry-safe notifications possible. Alert delivery failure needs its own visible signal. Keep routing and on-call configuration auditable.',
'Check ingestion lag, missing targets, evaluation delay, and notification success. Redundant monitoring or an external probe catches failure of the main monitoring stack. Avoid using raw private user data in labels. Bound query cost and isolate expensive users.'
], '''### Contract
Alert when checkout error rate stays above 5% for five minutes. Only page if enough requests occurred.
### Size
100 instances ×10 metrics × one sample/10 seconds =100 samples/s before label combinations.
### Model
Series(name, labels) and timestamped samples. Alert state is separate durable state.
### Flow
Collect → ingest → query a five-minute window → pending/firing rule → grouped notification.
### Stress
Predict: zero samples arrive. Is error rate zero?

No. Evaluate missing-data health separately. A denominator of zero does not prove success.
### Operate
Test a synthetic failing request and confirm that someone receives the alert.
### Explain
Store request IDs in traces, not as unbounded metric labels.''', [
'Collect service latency, traffic, errors, and saturation. Dashboard freshness under30 seconds. Page after a sustained five-minute checkout error condition with a traffic floor; handle missing data separately.',
'10,000 instances ×100 series each /10-second interval =100,000 samples/s. At16 bytes raw/sample, one day is about138 GB before labels/indexes/replication. Cardinality is a separate capacity dimension.',
'Series identified by name and allowed labels; samples by timestamp. AlertRule and AlertState store thresholds, duration, fingerprint, destinations, and last notification. Separate samples from alert delivery state.',
'Collectors buffer bounded samples; ingestion validates labels/timestamps; time-series storage accepts writes; evaluators read windows; sustained conditions create grouped alert state; notification workers retry safely.',
'Test collector outage, partial scrape failure, duplicate sample, expensive query, and notification timeout. Missing data triggers a distinct health rule. Preserve alert state across evaluator failover to avoid duplicate pages.',
'Watch ingestion age, missing targets, query p95, evaluator delay, and notification delivery. Downsample older data under an explicit retention policy. Add an external probe and regularly test paging.',
'Pull simplifies target health visibility; push suits some short-lived or constrained jobs. Rich labels improve debugging but grow series count. Long windows reduce noise but delay detection.'
], ('A checkout monitoring platform', 'Design monitoring for 10,000 instances with100 series each, sampled every ten seconds. Dashboards should be under30 seconds old. Alert on sustained checkout errors for five minutes, with a traffic floor. Include cardinality limits, missing data, and notification failure.'),
('Every request adds a new label', 'A team adds request_id to a latency metric. Explain the damage and give another way to debug one request.'),
'Each distinct request ID creates a separate series, multiplying index/storage costs and weakening aggregation. Remove the unbounded label, keep bounded service/region/status dimensions, and use traces or logs for request-level detail. Link a sampled trace from an aggregate metric if supported. Add ingestion label/cardinality budgets.',
('A misleading quiet dashboard', 'Bad rule: if no samples exist, display zero errors and resolve every alert. Repair it.'),
'Represent missing/stale data explicitly. Evaluate target availability and ingestion freshness separately from service error rate. A service rule needs a valid denominator and sufficient traffic; missing telemetry must not erase a still-unresolved incident. Test a collector outage while the application is failing.', [
('Which label is most likely to cause unbounded series growth?', 'A unique request ID.', 'A bounded deployment region.', 'A fixed HTTP status class.', 'A fixed service name.', 'The number of unique label combinations determines series cardinality.'),
('No samples arrive. Which conclusion is valid?', 'Telemetry freshness is unknown or unhealthy.', 'The service has zero errors.', 'All users are happy.', 'All pending alerts should resolve.', 'No data and a measured zero are different states.'),
('Why keep pending/firing alert state?', 'To require a sustained condition and control repeated notifications.', 'To avoid storing metrics.', 'To guarantee every error pages immediately.', 'To replace all dashboards.', 'State lets the rule distinguish a transient spike from a sustained incident.'),
('What verifies the full monitoring path?', 'A synthetic failure that reaches an observed notification.', 'Only checking collector CPU.', 'Only counting dashboards.', 'Only storing more labels.', 'Collection, evaluation, routing, and delivery must all work.')],
'''flowchart TD
  A["Applications"] --> C["Collectors and bounded buffer"]
  C --> I["Validate samples and labels"]
  I --> T["Time-series storage"]
  T --> D["Dashboards"]
  T --> E["Windowed rule evaluation"]
  E --> S["Pending or firing alert state"]
  S --> N["Grouped retry-safe notification"]
  H["External health probe"] --> N''', ['Choose user symptoms', 'Bound label combinations', 'Collect and store samples', 'Evaluate sustained windows', 'Group, deliver, and test alerts', 'What if the collector stops sending data?'])

add('22-event-aggregation', 'Count events without counting twice', 6, '159–194', 5, '20 message queue; 12 autocomplete', [
('Keep raw facts and useful totals', 'Raw events let you rebuild a total. Aggregates make reads cheap. Give each event a stable identity.', 'A retry of the same click must not become a new click.', 'One fact. One identity.'),
('Choose the clock', 'Event time says when the click happened. Processing time says when the server handled it. Delays make them different.', 'A phone offline for two minutes uploads an older click now.', 'Arrival time is not event time.'),
('Define late data rules', 'A window groups events by time. Decide how long to wait for late events and whether published totals can be corrected.', 'A 12:00 click arriving at12:03 may update an earlier minute.', 'A final total needs a lateness policy.'),
('Make replay safe', 'Save processing state and output consistently, or use versioned/upserted results. Restarting from a checkpoint must not add the same partial total twice.', 'Writing +100 twice after a crash doubles the result.', 'Replaying a batch must replace or deduplicate its effect.'),
('Handle hot keys and backfills', 'A popular ad can overload one worker. Split partial counts, then combine them. Keep rebuild output separate until validated.', 'Recomputing yesterday should not add yesterday a second time.', 'Rebuild alongside. Compare. Switch.')], [
'Define counted event, deduplication scope, dimensions, and correction policy. Retain raw events under a privacy and cost budget. Separate operational dashboards from billing-quality finalized totals. A stable event_id must represent the same logical event across retries.',
'Window by event time if the product asks when the action happened. Client time needs sanity bounds or trusted attribution. Processing-time windows are simpler but move delayed actions into later buckets. State which promise you choose rather than mixing them.',
'A watermark is a progress estimate used to decide which windows are ready; it does not prove no older event will ever arrive. Allow bounded late updates and version corrected outputs, or route overly late events to a correction path. Explain what users see during changes.',
'Checkpoint source positions and aggregation state together under the chosen engine semantics. Write output with a stable window/key/version identity or a transaction. Dedup state needs retention covering the supported replay horizon. Exactly-once totals require agreement among source, state, and sink.',
'Salt a hot aggregation key into partial shards and merge partials once per stable shard/window/version. Backfill to a new result version, compare against raw data and independent samples, then switch readers. Observe lag, late-event fraction, dedup drops, hot-key load, and reconciliation differences.'
], '''### Contract
Count page opens per minute. Live totals may change for five minutes; then publish a corrected final view.
### Size
10,000 events/s ×200 bytes =2 MB/s before replication. Store keys and dedup state too.
### Model
Event(id, page, event_time). Result(page, minute, revision, count).
### Flow
Retained log → dedup → event-time window → versioned result → dashboard.
### Stress
Predict: a worker writes a total then restarts before its checkpoint.

Replaying must upsert the same window revision or use a consistent state/output commit. Blindly adding again is wrong.
### Operate
Track processing lag and late-event fraction. Preserve raw data long enough for supported rebuilds.
### Explain
A low-latency view can be provisional. The final count needs an explicit correction rule.''', [
'Count ad clicks by ad, country, and minute. Dashboard updates within ten seconds. Accept late data for five minutes; later arrivals go to correction processing. Deduplicate stable event IDs.',
'100,000 events/s ×200 bytes =20 MB/s, about1.73 TB raw/day before replication. Estimate dedup-state size from replay horizon and IDs/s, not only result-row count.',
'Click(event_id, ad_id, event_time, country); source partition/offset; result keyed by ad/country/minute plus revision. Keep raw input and processing checkpoints; define ID scope and retention.',
'Ingest durable events, validate timestamp bounds, deduplicate, assign event-time windows, combine partial counts, and publish versioned results. Track progress per partition and document late correction behavior.',
'Replay a checkpoint, duplicate one click, delay a partition, and overload a hot ad. A watermark cannot guarantee no late event. Use stable output identities and consistent checkpoints; split hot keys and combine without repeating partial contributions.',
'Observe lag, duplicates, late arrivals, state size, and totals versus raw sampled recomputation. Backfill to a separate version; validate and switch readers atomically. Keep auditable corrections without retaining unnecessary personal fields.',
'Faster provisional counts trade certainty for freshness. Longer lateness windows need more state and delay finality. Global dedup forever is expensive; state the supported horizon.'
], ('Live ad-click totals', 'Design counts for100,000 click events/s of200 bytes each, grouped by ad/country/minute. Dashboard lag under ten seconds. Late events may correct totals for five minutes. Handle duplicate delivery, hot ads, restart, and a backfill without double counting.'),
('A billing team needs finalized totals', 'Live dashboards accept revisions. Billing now needs reproducible finalized totals. What extra boundary and evidence are needed?'),
'Publish a versioned finalized dataset after a stated lateness cutoff and correction policy. Preserve input ranges/checkpoints, aggregation version, dedup rules, and reconciliation evidence. Later corrections create a new auditable adjustment/version instead of silently changing an issued result. Avoid claiming the watermark proves all possible events arrived.',
('A backfill doubles totals', 'Bad rebuild: replay all raw events and increment the same live counter again. Repair the rebuild procedure.'),
'Write recomputed results into a new version keyed by aggregation dimensions and window. Deduplicate according to stable event identity and replay horizon. Compare totals, samples, and input coverage, then switch the reader manifest. Retain rollback. Do not merge a complete replacement dataset as additional increments.', [
('A12:00 click arrives at12:03. Which time defines an event-time window?', 'The12:00 event timestamp, under its validation rules.', 'Always12:03.', 'The browser timezone string alone.', 'The time the dashboard is opened.', 'Event time follows the action time rather than processing arrival.'),
('Does a watermark prove no older event can arrive?', 'No; late-data behavior still needs a policy.', 'Yes, by physical law.', 'Only if counts are cached.', 'Yes, if partitions have names.', 'A watermark estimates progress; delayed data can still occur.'),
('What makes replay-safe output possible?', 'Stable result identity with consistent state or replace/upsert semantics.', 'Unconditional increments on every restart.', 'Deleting all event IDs.', 'Using random output IDs per retry.', 'The sink must recognize a replayed contribution rather than add it again.'),
('How should a full backfill reach live readers?', 'Validate a separate result version and switch readers.', 'Increment every live total with all old events.', 'Clear checkpoints and hope.', 'Hide raw-data differences.', 'A replacement computation is not an extra contribution.')],
'''flowchart TD
  E["Events with stable IDs and time"] --> L["Retained event log"]
  L --> D["Deduplicate supported replay"]
  D --> W["Event-time windows"]
  W --> P["Merge partial counts"]
  P --> V["Versioned aggregate results"]
  V --> Q["Dashboard or finalized view"]
  R["Raw-data replay"] --> B["Separate backfill version"]
  B --> V''', ['Define the counted fact', 'Keep identity and event time', 'Choose windows and lateness', 'Checkpoint and publish safely', 'Validate backfills before switching', 'What if one event arrives twice after a restart?'])

add('23-reservations', 'Reserve inventory without overselling', 7, '195–224', 5, '02 correctness; 08 async', [
('Search is a hint. Booking is a promise.', 'A search result may be a little old. A confirmed booking must reserve real inventory.', 'Two people can both see one room left. Only one may book it.', 'Recheck at the write boundary.'),
('Model every night', 'Hotels usually sell a room type for a date range. Check each night, not just one availability flag.', 'A Friday-to-Sunday stay uses Friday and Saturday night inventory.', 'One stay. Several inventory rows.'),
('Make one atomic decision', 'Check and reserve all required nights in one transaction. Use locks or conditional versions so two requests cannot both win.', 'Reading available=1, then writing0 later allows two winners.', 'Check and change together.'),
('Separate holds and payment', 'A short hold can protect inventory during payment. Give it an expiry and explicit state. A timeout is not proof payment failed.', 'A successful payment can arrive after the hold expires. The system needs a policy for that case.', 'Every pending state needs an exit.'),
('Retry safely and reconcile', 'Use a stable booking request ID. Repeating the request should return its existing result, not reserve another room.', 'The client lost the reply but the booking was committed.', 'Retry the identity. Do not create a new booking.')], [
'Define whether inventory is per room or room type, whether overbooking is allowed, and how payment relates to confirmation. This exercise forbids overselling. Search can use cached availability, but the authoritative booking transaction must recheck all nights.',
'Inventory(hotel_id, room_type, date, capacity, held, confirmed, version) supports a date-range stay. Reservation(id, user, dates, status, hold_expiry, request_key) records intent. A single is_available boolean cannot represent availability across arbitrary date ranges.',
'Lock inventory rows in a stable date order, or use conditional versioned updates with retry of the whole transaction. Ensure every night has capacity before committing any decrement. A failed night rolls back the whole reservation. Unique request keys handle client retries.',
'Keep held, confirmed, expired, canceled, and payment_unknown transitions explicit. Releasing a hold and accepting a payment success must race through a conditional state transition. A late success may require a refund if inventory can no longer be reserved; never silently overbook.',
'Observe booking conflicts, hold age, abandoned inventory, payment unknowns, and oversell checks. Reconcile provider outcomes with local state. A cache must not decide correctness. Test overlapping date ranges and expiry versus success, not only two identical requests.'
], '''### Contract
Sell one remaining room for Friday night. No overbooking. Payment can be delayed.
### Size
The dangerous load is simultaneous bookings for the same room type and night, even when total traffic is small.
### Model
Inventory(date, capacity, held, confirmed) and Reservation(request_key, state, expiry).
### Flow
Lock the inventory row → verify capacity → create hold and request identity → commit. Pay using the same operation identity.
### Stress
Predict: two buyers read one remaining room before either writes.

A separate read then write oversells. One atomic guarded transaction lets only one reserve it.
### Operate
Expire abandoned holds through a state transition. Reconcile late payment success.
### Explain
Cached search helps speed. Authoritative inventory decides the booking.''', [
'Reserve room types for check-in inclusive/check-out exclusive dates. No overselling. Search may lag30 seconds; booking is authoritative. Hold inventory for five minutes during payment and define late-success behavior.',
'100,000 searches/s and1,000 booking attempts/s are different paths. A popular hotel/date can concentrate conflicts. Estimate rows per stay and transaction duration; partition by hotel while keeping a stay transaction local.',
'Inventory(hotel, type, night, capacity, held, confirmed, version); Reservation(id, owner, dates, state, expires_at, request_key); PaymentAttempt with stable provider key. Unique request identity and authorized ownership checks.',
'In one transaction lock all nights in stable order, verify capacity, create a hold and request result, update inventory, and commit. Payment proceeds outside the database lock. Conditional transitions convert the live hold to confirmed or release it.',
'Test two buyers for the last room, one unavailable middle night, duplicate requests, and payment success racing expiry. Roll back all nights on failure. A late success after release needs explicit re-reservation/refund policy, not forced confirmation.',
'Monitor conflicts, hold expiry lag, stale search age, unknown payment outcomes, and inventory consistency. Use an outbox for confirmations. Reconcile payment state. Test recovery of an expiry worker after an outage.',
'Pessimistic locks simplify contention reasoning but can wait/deadlock; stable lock order helps. Optimistic versions work under lower contention but need whole-transaction retry. A cache lock alone is not the authoritative inventory rule.'
], ('Rooms across several nights', 'Design hotel room-type booking:100,000 searches/s and1,000 booking attempts/s. Search may lag30 seconds. Never oversell any night. Hold rooms for five minutes during payment. Cover multi-night transactions, retries, expiry, and a late payment success.'),
('An assigned seat instead', 'The business now sells exact seats for a show, not pooled room types. What changes in keys, holds, and concurrency?'),
'Use show_id/seat_id as the inventory identity and a conditional transition from available to held with owner/expiry/version. A unique active seat allocation prevents double sale. A multi-seat booking needs an all-or-nothing policy or explicit partial acceptance. Payment, expiry races, request deduplication, and late-success handling still apply. The date-range capacity loop becomes exact-seat state transitions.',
('Two winners for one room', 'Bad code: if read_available(night)>0: create_booking(); decrement(night). Repair it for a three-night stay.'),
'Begin one transaction, lock all three inventory rows in deterministic order, verify each available capacity, then update every row and insert the unique-request reservation. Commit once. If any night fails, roll back all changes. Alternatively use versioned conditional updates with whole-transaction conflict retry. Prove correctness with two concurrent overlapping stays.', [
('Why can cached search availability not confirm a booking?', 'Another booking may change inventory before confirmation.', 'Caches cannot store numbers.', 'Search has no users.', 'A longer TTL prevents races.', 'The authoritative transaction must recheck capacity at commit time.'),
('A three-night stay has no capacity on night two. What should happen?', 'The whole reservation transaction fails without partial inventory loss.', 'Reserve nights one and three silently.', 'Confirm because most nights work.', 'Decrease capacity below zero.', 'The booking promise spans every required night.'),
('What protects a retried request after a lost response?', 'A unique durable request identity and stored outcome.', 'A random booking ID on each retry.', 'Disabling all client retries.', 'Only a browser spinner.', 'The retry must find the original operation rather than allocate again.'),
('Payment succeeds after a hold was released. What is required?', 'An explicit conditional recovery or refund policy.', 'Always oversell to honor payment.', 'Forget the provider response.', 'Call the timeout a failure forever.', 'The payment result and inventory state must be reconciled honestly.')],
'''flowchart TD
  U["Booking request and stable ID"] --> T["Transaction: lock every night"]
  T --> C["Capacity on all nights?"]
  C --> H["Create expiring hold and commit"]
  H --> P["Payment outside inventory lock"]
  P --> S["Conditional success or unknown state"]
  S --> B["Confirm live hold"]
  H --> E["Expiry worker: release if still held"]
  S --> R["Reconcile late result or refund"]''', ['Search may be stale', 'Lock all required inventory', 'Create one retry-safe hold', 'Pay without holding database locks', 'Confirm or expire conditionally', 'What if payment succeeds just after expiry?'], lab='reservation')

add('24-email', 'Deliver and search email', 8, '225–252', 4, '08 notifications; 12 search; 14 file sync', [
('Submission is not inbox delivery', 'Sending email has several states. A server may accept a message while the recipient server has not accepted it yet.', 'The recipient server is down. The outgoing message stays queued for retry.', 'Accepted here does not mean delivered there.'),
('Separate content and mailbox state', 'Keep large bodies and attachments in blob storage. Keep mailbox ownership, folders, flags, and message IDs in indexed records.', 'Marking a message read should not rewrite its50 MB attachment.', 'Bytes and mailbox state have different jobs.'),
('Build retry-safe delivery', 'An outbound queue retries temporary failures. Keep a stable internal identity and delivery attempts. Stop on permanent failure or policy expiry.', 'A connection drops after the remote server accepts the mail but before its reply arrives.', 'An uncertain remote outcome can still duplicate mail.'),
('Search is a private derived view', 'Build a search index from stored mail. Check mailbox ownership again when returning results. Deletes must reach both views.', 'A stale search index must not show a message from another user’s mailbox.', 'Search helps find. Ownership allows access.'),
('Abuse and recovery are core paths', 'Limit sending, inspect unsafe attachments, protect credentials, and recover queued work after a crash.', 'One compromised account should not exhaust every sender’s quota.', 'Protect the recipient and the shared service.')], [
'Distinguish client submission, durable local acceptance, remote SMTP acceptance, recipient mailbox placement, and read state. Protocol acceptance cannot prove a human saw the mail. Specify temporary/permanent failure handling and a visible delivery status model.',
'Store immutable body/attachment blobs with size and integrity metadata. MailboxEntry(user_id, message_id, folder, flags, version) provides user-scoped queries and synchronization. Deduplication of shared blobs is separate from authorization of every mailbox reference.',
'Commit outgoing intent before returning accepted. Workers lease attempts, obey per-domain limits, retry temporary errors with backoff, and create a bounce/failure record for permanent errors. A remote timeout may be unknown. Internal deduplication cannot force every SMTP recipient to deduplicate.',
'An outbox/change stream feeds the mailbox search index. Version-aware events avoid restoring deleted mail. Check current mailbox membership and deletion policy on result hydration. Define index freshness and removal deadlines; do not make search the source of truth.',
'Inbound boundaries validate size and identity policy, scan attachments under a quarantine state, and enforce abuse budgets. Observe delivery age, domain failures, spam complaints, search lag, and storage integrity. Keep private message content out of routine logs; audit authorized access.'
], '''### Contract
A small team mail service stores mail and retries temporary remote failures for24 hours. Search may lag30 seconds.
### Size
10,000 messages/day ×100 KB average ≈1 GB/day before copies and attachments.
### Model
Message body blob, user-scoped mailbox entry, and durable outbound attempt state.
### Flow
Commit content plus outgoing intent → acknowledge submission → delivery worker contacts recipient server → record result.
### Stress
Predict: the remote server accepted the message, but its reply was lost.

Keep the outcome uncertain and follow retry/reconciliation policy. Do not claim exactly-once external delivery.
### Operate
Track oldest pending delivery and permanent failures. Search filters by current mailbox access.
### Explain
The inbox view, content store, search index, and delivery queue solve different access patterns.''', [
'Provide client submission, mailbox listing, read flags, attachment download, and private search. Local accepted means durable content plus delivery intent. Remote acceptance/read are separate states; search may lag30 seconds.',
'Two million messages/day at100 KB average =200 GB/day raw before attachments and replication. Size peak SMTP connections, mailbox reads, and search independently. Large attachments dominate tail storage and bandwidth.',
'Message(id, body_ref, attachment_refs, integrity); MailboxEntry(user, message, folder, flags, version); Delivery(id, destination, state, attempts, next_try). Stable internal send key deduplicates client retries.',
'Validate sender and size, persist content and local mailbox/delivery intent durably, then return accepted. Delivery workers use per-domain concurrency and retries. Change events feed search. Result hydration rechecks user mailbox ownership.',
'Test lost submit response, remote acceptance with lost reply, duplicate inbound mail, stale search deletion, and worker restart. Preserve uncertain remote outcomes; do not promise unique external delivery without recipient cooperation.',
'Observe queue age, domain rejection, bounce rate, search lag, blob integrity, and abuse quotas. Quarantine suspicious attachments, protect credentials, and audit access without copying message bodies into logs.',
'An external search engine speeds development but adds synchronization and privacy boundaries. A custom index adds maintenance cost. Blob content and small mutable mailbox records should evolve independently.'
], ('A team email service', 'Design email submission, inbox listing, read flags, attachments, and private search for two million messages/day at100 KB average. Search may lag30 seconds. Explain durable acceptance, remote retries, uncertain delivery, deletion, and abuse limits.'),
('Urgent mailbox deletion', 'A user deletes a message and it must disappear from search immediately, even though indexing takes30 seconds. How?'),
'Commit a tombstone/current mailbox visibility change in the authoritative mailbox store. Search may still return the stale ID, but hydration filters it against current access/deletion state. Purge index entries asynchronously and apply the stated blob retention/legal policy separately. Test stale index pages and direct attachment URLs with expiring scoped access.',
('Remote timeout means resend forever', 'Bad worker: any timeout creates a new message ID and retries immediately forever. Repair identity, retry policy, and status.'),
'Reuse the original logical send identity and keep a durable delivery-attempt record. A timeout is unknown; retry under bounded time/attempt policy with backoff and domain limits. Record remote references where available. Distinguish permanent rejection from transient failure. Internal identity prevents duplicate local work, but arbitrary SMTP recipients may still see duplicate delivery.', [
('What does local accepted most safely mean?', 'Content and delivery intent are durably stored.', 'The recipient read the message.', 'Every remote server is online.', 'The attachment was downloaded.', 'Submission, remote acceptance, inbox placement, and reading are separate states.'),
('Where should read/unread state live?', 'In user-scoped mutable mailbox records.', 'Only inside the attachment bytes.', 'Only in the search index.', 'In every SMTP retry key.', 'Small mutable mailbox state should not require rewriting large content.'),
('What protects private search results?', 'Current mailbox ownership checks when results are returned.', 'Only a hard-to-guess message ID.', 'A shared cache without user scope.', 'A longer index refresh interval.', 'A stale derived index must not grant current access.'),
('Can an internal message ID guarantee exactly-once SMTP delivery?', 'No; the remote effect needs cooperation or a weaker promise.', 'Yes for every recipient server.', 'Yes if retries use random IDs.', 'Yes if attachments are cached.', 'A lost remote reply can leave an uncertain accepted outcome.')],
'''flowchart TD
  U["Authenticated sender"] --> S["Validate and store send intent"]
  S --> B["Body and attachment blobs"]
  S --> M["User mailbox metadata"]
  S --> Q["Durable outbound queue"]
  Q --> R["Remote server and retry policy"]
  M --> I["Private search index"]
  I --> A["Current mailbox access check"]
  A --> C["Recipient mailbox view"]''', ['Separate submission from delivery', 'Store bytes and mailbox state', 'Retry with durable identity', 'Index then check current ownership', 'Watch age, abuse, and recovery', 'What if the remote reply is lost after acceptance?'])

add('25-object-storage', 'Store objects and keep them intact', 9, '253–288', 5, '07 storage; 13 media; 14 file sync', [
('Separate names from bytes', 'Metadata maps a bucket and key to a committed object version. Storage nodes hold the bytes.', 'Renaming a pointer should not move every byte through the API server.', 'Metadata finds. Data nodes carry.'),
('Commit after the bytes are safe', 'Upload parts to storage, check integrity, then publish a complete object version. Incomplete uploads must not appear as valid objects.', 'A broken upload has four of five parts. Readers should not receive a partial file as complete.', 'Upload → verify → publish.'),
('Copies and coding have costs', 'Replication keeps full copies. Erasure coding keeps data and repair pieces. Coding can save space but makes reads and repair more complex.', 'Three copies of100 TB use about300 TB before overhead.', 'Space saved can become repair work.'),
('Listing is its own access pattern', 'Looking up one object by key and listing keys by prefix need different index support. Hashing names evenly does not make sorted listing cheap.', 'photo/2026/ may span many metadata shards.', 'Spread writes. Plan ordered reads.'),
('Repair and garbage collection', 'Check stored pieces for corruption and rebuild missing ones. Delete unreferenced uploads only after proving no committed object still needs them.', 'A slow upload must not lose parts because a cleanup worker guessed it was abandoned.', 'Deletion needs ownership, state, and a grace rule.')], [
'Object APIs operate on bucket/key/version identities. Metadata stores ownership, placement, size, checksum, and commit state. Data nodes serve large byte streams directly under scoped authorization. A metadata cache must not expose private or deleted content.',
'Multipart uploads have an upload identity and part identities/checksums. Completion verifies the expected parts and commits one visible version conditionally. Concurrent overwrites need a defined version/order policy. Acknowledgment is tied to the durability contract, not merely receipt by a gateway.',
'With k data and m parity pieces, ideal space expansion is(k+m)/k, but fault tolerance requires pieces across independent failure domains. Coding does not remove metadata or repair needs. Durability probability and availability depend on failure correlation, detection, repair bandwidth, and enough remaining readable pieces.',
'Hash(bucket,key) balances direct metadata lookup but prefix listings need an ordered secondary index or scatter/gather with a cursor contract. Define snapshot/listing consistency under concurrent writes. Avoid promising filesystem hierarchy or atomic folder rename from slash characters alone.',
'Scrubbing detects silent corruption using checksums. Repairs are scheduled with bandwidth/capacity limits. Garbage collection uses committed references, upload expiry/state, and grace periods; retain versions/tombstones as required. Observe repair backlog, missing pieces, integrity failures, and metadata/data mismatch.'
], '''### Contract
A backup client uploads a100 MB object in five parts. GET exposes only a complete version.
### Size
Three full copies need300 MB, before metadata and protocol overhead. A4+2 code uses150 MB ideally, with more repair work.
### Model
Upload(id, parts, expiry), Object(bucket,key,version,state,placement,checksum).
### Flow
Upload parts → verify checksums → satisfy durability rule → commit metadata pointer → serve reads.
### Stress
Predict: completion reply is lost. Should retry create another unrelated object?

Use the same upload identity and conditional completion result. Return the committed version again.
### Operate
Scrub pieces and test repair. Clean orphan parts only through the upload lifecycle.
### Explain
Cheap space is not the only target. Repair speed and failure domains matter.''', [
'GET/PUT/DELETE and prefix LIST for private objects, up to5 GB each. A successful completed PUT exposes one complete version. Specify overwrite/list consistency and supported node/rack failures.',
'Assume1 PB logical data: three replicas need3 PB before overhead. A6+3 erasure code has1.5x ideal expansion. Compare repair traffic and spare capacity; include multipart remnants and older versions.',
'Bucket ownership; Object(bucket,key,version,state,size,checksum,placement); Upload(id,parts,expiry); storage-piece records across failure domains. Ordered listing index is separate from balanced direct lookup.',
'Authenticate, allocate upload, send parts to data nodes, verify integrity and required durable placement, then atomically publish the committed version. Reads resolve current authorized metadata and stream verified pieces.',
'Fail upload midway, lose completion reply, corrupt a piece, lose a rack, and race overwrite/delete. Retry completion by upload ID. Do not expose incomplete bytes. Verify coding pieces lie in distinct failure domains and repair before redundancy is exhausted.',
'Observe incomplete uploads, repair backlog/age, checksum failures, free capacity, and metadata mismatch. Rate-limit repair against serving capacity. Garbage-collect only safely unreferenced/expired data with a grace protocol. Test restore, not only replication.',
'Replication is simpler and fast for small/hot objects; erasure coding reduces expansion for larger/cold objects but costs CPU and repair bandwidth. Prefix listing requires planned indexes; hashing alone does not provide it.'
], ('A private backup object store', 'Design private object storage with GET/PUT/DELETE and prefix LIST. Store1 PB logical data with objects up to5 GB. Publish only complete uploads. Compare replication and6+3 coding. Explain metadata, checksums, failure domains, orphan cleanup, and repair.'),
('A rack disappears', 'A6+3 coded object has all nine pieces on one rack. Explain why the code does not protect against a rack loss and repair the placement policy.'),
'A code survives loss of at most three pieces only if enough independent pieces remain. Losing the rack loses all nine. Spread pieces across independent rack/zone failure domains under an explicit policy, reserve repair capacity, monitor placement violations, and test loss of the largest supported domain. Durability is not just the number of parity pieces.',
('Partial upload becomes visible', 'Bad code: create visible object metadata, upload parts, then return success. A worker may crash mid-upload. Repair publication and cleanup.'),
'Use an uploading state separate from visible committed versions. Upload and verify all parts, satisfy the declared durability boundary, then publish the complete version with a conditional transaction. Keep completion idempotent by upload ID. Garbage-collect abandoned parts by expired upload state and reference checks; never delete parts referenced by a committed version.', [
('When should a complete object become visible?', 'After required bytes are verified and the committed version is published.', 'As soon as the first part arrives.', 'Before any storage node responds.', 'Whenever a gateway allocates an ID.', 'Visibility is a commit decision, not proof that upload started.'),
('What is ideal expansion for6+3 erasure coding?', '1.5 times logical size.', 'Three times.', 'One third.', 'Zero extra storage.', '(6+3)/6=1.5, before metadata and operational overhead.'),
('Does hash-based key lookup solve prefix listing?', 'No; ordered listing needs its own index or scatter/gather plan.', 'Yes, automatically sorted on every shard.', 'Only if objects are large.', 'Yes, slash characters create transactions.', 'Balanced direct lookup and sorted range access are different patterns.'),
('What makes garbage collection safe?', 'Lifecycle/reference checks and a defined grace rule.', 'Deleting every part older than one minute.', 'Assuming uploads never pause.', 'Ignoring committed versions.', 'A slow or retried upload can still legitimately need its parts.')],
'''flowchart TD
  C["Client and upload ID"] --> M["Metadata: upload state"]
  C --> D["Data nodes: parts and checksums"]
  D --> V["Verify durable placement"]
  V --> P["Publish complete object version"]
  P --> G["Authorized GET and LIST"]
  D --> S["Scrub and repair across failure domains"]
  M --> X["Safe orphan cleanup"]''', ['Name objects and versions', 'Upload parts with integrity checks', 'Place pieces across failure domains', 'Publish only a complete version', 'Scrub, repair, and clean safely', 'What if completion succeeds but the reply is lost?'])

add('26-leaderboard', 'Rank players with clear rules', 10, '289–314', 4, '02 caches; 20 queue', [
('Define what rank means', 'Decide whether scores are totals, best scores, or latest scores. Specify ties and the season boundary.', 'Two players have100 points. The product must say whether they share a rank.', 'A ranking needs a comparison rule.'),
('Use an ordered score index', 'A sorted set can support score changes, top players, and player rank. Keep player identity as a stable member.', 'A hash table finds a score quickly but does not directly give everyone’s order.', 'Point lookup and ordered lookup differ.'),
('Trust validated game results', 'Clients should not freely write their own final score. Apply each validated match result once.', 'A retry of a10-point match must not add another10 points.', 'Validate once. Apply once per result ID.'),
('Split carefully', 'A single ordered index is easy until it is too large or hot. Shards can produce local top lists, but exact global rank needs more work.', 'A player is rank10 on one shard. That does not tell their worldwide rank.', 'Local rank is not global rank.'),
('Rebuild without mixing seasons', 'Keep score events or authoritative totals so the serving index can be rebuilt. Key every result by season.', 'A delayed result from last season must not change this season’s board.', 'Season is part of the identity.')], [
'Define rank convention: competition rank(1,1,3), dense rank(1,1,2), or a unique order with a deterministic tie-breaker. Different sorted-set APIs may return positions rather than the desired shared rank. State freshness and whether exact global rank is required.',
'For moderate scale, a sorted set per season supports ordered queries while a durable score source provides recovery. Store player details separately and hydrate only returned IDs. Score precision and tie-break encoding need care; do not lose integer accuracy in a packed floating-point score.',
'Validate results server-side. A stable match/result ID and unique applied-event record prevent repeated increments. Commit deduplication and durable score change together, then update the derived sorted index through replay-safe events. A cache command alone does not make the whole workflow durable.',
'Top-K merges can be efficient: ask each shard for its local top-K, then merge. Exact rank of an arbitrary player needs the number of players ahead across all shards under a consistent snapshot/freshness contract. A simple local-rank lookup cannot answer it.',
'Use season_id in input, totals, and ordered-index keys. Rebuild a new index from a trusted checkpoint plus tail, validate top/rank samples, then switch. Track score-to-index lag, replay duplicates, memory, hot players, and rank-query latency.'
], '''### Contract
A weekly quiz ranks by total valid points, then earlier completion time. Scores may lag two seconds.
### Size
100,000 players with about100 bytes of raw score metadata is10 MB before sorted-index overhead and copies.
### Model
Result(result_id, season, player, delta) and authoritative total; a derived ordered index serves rank.
### Flow
Validate result → atomically deduplicate and add points → update ordered index → fetch top players.
### Stress
Predict: the same result arrives twice.

The durable applied-result identity makes the second update a no-op. Repeating an increment without that check is unsafe.
### Operate
Track index lag and rebuild from totals.
### Explain
The sorted index is excellent for serving. It is not by itself the complete scoring rule or recovery record.''', [
'Weekly leaderboard, valid match points, exact top100, player position, deterministic ties, and two-second score freshness. Define whether position or shared rank is required; exclude client-authoritative scores.',
'Ten million players and20,000 score events/s. Estimate real sorted-index overhead and replication memory, not only raw score bytes. Benchmark one board before sharding; arbitrary-rank queries add read cost.',
'Result(event_id, season, player, validated_delta); authoritative totals and applied-event IDs; season-scoped ordered projection. Tie ordering includes an explicit stable secondary field. Player profile is separate.',
'Validate trusted match result, commit deduplication plus score total, publish replay-safe projection update, then serve top100/rank with bounded freshness. Include the projection version/age where useful.',
'Test repeated result, out-of-order projection update, season rollover, and index loss. Apply total versions rather than stale additive cache updates. Exact global position after sharding needs counts ahead across shards with a consistency contract.',
'Observe index lag, duplicate IDs, memory/headroom, hot players, and query p95. Rebuild next to live index from checkpoint plus tail; validate and switch. Reject results for the wrong season.',
'One sorted index is simple but has memory/write limits. Sharded top-K merging is tractable; exact arbitrary rank costs cross-shard work. Weaker approximate rank may be a product option, never an unstated substitution.'
], ('A weekly game leaderboard', 'Design a board for ten million players and20,000 score events/s. Return top100 and each player’s position within two seconds of a validated result. Define ties, retry safety, season rollover, rebuild, and the limits of sharding.'),
('Only top100 is needed', 'Remove arbitrary-player rank from the requirements. How does the sharded serving path become simpler?'),
'Each shard returns its local top100 under the same season and tie ordering. Merge those lists to choose the global top100. A player outside their shard top100 cannot enter the global top100 because at least100 players in that shard already precede them. State snapshot/freshness limits; this does not solve exact arbitrary global rank.',
('Duplicate score increments', 'Bad handler: receive match result; increment sorted-set score; acknowledge. A timeout causes the same result to be sent again. Repair it.'),
'Persist a stable validated result ID and atomically apply it with the authoritative total exactly once within that transaction. Publish a versioned total update to the serving index; consumers ignore older versions/repeated updates. A separate dedup write after the increment leaves a crash gap. Rebuild the index from durable totals if lost.', [
('Why define tie rules before picking a rank API?', 'Position and shared-rank conventions can produce different answers.', 'All products use the same tie rule.', 'Ties disappear with replication.', 'Rank is always alphabetical.', 'A sorted position is not automatically the product’s requested rank.'),
('What makes score retries safe?', 'A stable validated result ID tied atomically to the durable score change.', 'A new random ID on every retry.', 'Trusting any browser score.', 'Only a longer cache TTL.', 'The result identity must share the transaction with its effect.'),
('Can local rank10 identify global rank?', 'No; other shards may contain players ahead.', 'Yes, always10.', 'Only if the name is unique.', 'Yes, after adding a CDN.', 'Global rank requires information about the rest of the population.'),
('What prevents old-season events affecting a new season?', 'Season identity on input, totals, and serving keys.', 'Clearing only the UI heading.', 'Keeping one forever-shared counter.', 'Sorting by username.', 'The boundary must be part of the data model and validation.')],
'''flowchart TD
  G["Validated game result and ID"] --> D["Transaction: dedup and score total"]
  D --> E["Versioned score event"]
  E --> S["Season ordered index"]
  S --> T["Top players"]
  S --> R["Player position under tie rule"]
  D --> B["Checkpoint and rebuild source"]
  B --> S''', ['Define scores, ties, and season', 'Validate a stable result ID', 'Commit dedup and score together', 'Update the ordered view', 'Serve rank and test rebuild', 'What if the same match result arrives twice?'])

add('27-payments', 'Handle payments and uncertain outcomes', 11, '315–340', 5, '08 async; 23 reservations', [
('A payment is a state machine', 'Track requested, pending, succeeded, failed, and unknown outcomes. A network timeout says the reply is missing, not that no money moved.', 'The provider charged successfully just before the connection broke.', 'Timeout means unknown.'),
('One intention needs one identity', 'Reuse a stable idempotency key for the same payment intent. Check that the amount and currency stay the same.', 'Clicking Pay twice must not create two independent charges.', 'Same intent. Same key. Same parameters.'),
('Keep provider state and local records aligned', 'Record the intent before calling the provider. Save its reference. Handle callbacks and status queries as repeatable state updates.', 'The callback may arrive before the original API reply.', 'Every path meets the same state transition.'),
('Record money with an audit trail', 'A payment status is not a ledger. Ledger entries explain what moved and why. Reconcile them with provider records.', 'A succeeded flag cannot explain a later refund or settlement difference.', 'Status tells where. Entries tell how much.'),
('Retry without hiding uncertainty', 'Retry transient failures under the provider’s documented key scope and expiry. Reconcile unknown or mismatched results.', 'A new key after each timeout can create a second charge.', 'Find the first outcome before creating another intent.')], [
'This is architecture practice, not a live payment integration. Separate authorization, capture, refund, and settlement according to product scope. Unknown is a durable state with a recovery action. Never infer provider failure merely from a missing response.',
'An idempotency record binds tenant/intent/key to request fingerprint and result. Unique creation and state transitions prevent local races. Provider keys have documented scope and retention; retain local operation identity and provider references beyond a single HTTP request.',
'Persist intent, execute the provider call without holding a long database lock, then record a conditional outcome. Authenticate and deduplicate webhooks; validate provider references and allowed transition order. Status queries and reconciliation repair missed callbacks. A late failure must not overwrite a confirmed success.',
'Use append-only balanced ledger entries under a defined currency and accounting boundary; corrections are new entries. Compare internal payments, ledger effects, and provider settlement/report data. Surface discrepancies for investigation rather than auto-inventing a matching state.',
'Use tokens rather than storing raw sensitive card data in this exercise. Enforce amount/currency ownership, least privilege, audit access, and safe logging. Observe unknown-outcome age, duplicate intent attempts, callback lag, reconciliation differences, and refund backlog.'
], '''### Contract
Pay100 units once for one order. The provider supports idempotency and status lookup. A lost reply remains pending/unknown.
### Size
Size peak calls and provider rate limits separately from order reads. More API workers do not increase provider quota.
### Model
PaymentIntent(id, order, amount, currency, state, provider_key, provider_ref).
### Flow
Persist intent → call provider with its stable key → conditionally store outcome → publish order update.
### Stress
Predict: the provider succeeds, the reply is lost, and the user retries.

Find the existing intent. Reuse the same provider key or query its status. Do not create a fresh charge key.
### Operate
Reconcile aged unknown states and settlement records. Keep secrets out of logs.
### Explain
Idempotency reduces repeated effects within its scope. Reconciliation handles remaining uncertainty.''', [
'One payment intent per order amount/currency revision. Distinguish pending, success, terminal failure, and unknown. Provider supports a bounded idempotency contract and status lookup. Refunds are separate linked operations.',
'2,000 payment requests/s peak, provider quota1,500/s. Admission/queueing must bound excess500/s and expiry; a growing queue is not extra quota. Size status-query and reconciliation traffic too.',
'PaymentIntent(id, owner, order, amount_minor, currency, fingerprint, state, provider_key/ref, version); webhook dedup record; ledger operation link; reconciliation record. Use integer minor units with currency rules.',
'Atomically create/find intent by stable scoped request key, verify fingerprint, and persist pending. Call provider with the same key. Conditional transitions unify replies, signed callbacks, and status checks. Commit local success plus downstream outbox atomically.',
'Test lost response after provider success, concurrent retry, duplicate/out-of-order callback, and key retention expiry. Keep unknown durable. Never retry under a new provider key while the original result may have succeeded; query/reconcile or escalate.',
'Observe unknown age, duplicate intent conflicts, provider errors/quota, callback lag, and settlement differences. Protect tokens, validate webhook signatures, restrict refunds, and keep audit records. Do not log raw payment credentials.',
'Provider idempotency helps but has scope/expiry and does not reconcile every bookkeeping discrepancy. Local transactions, repeatable remote identity, and reconciliation solve different failure boundaries.'
], ('A retry-safe checkout payment', 'Design payments peaking at2,000 requests/s against a provider quota of1,500/s. A payment may succeed even if its reply is lost. The provider has idempotency keys with finite retention and a status API. Cover intent identity, callbacks, ledger linkage, refunds, and reconciliation.'),
('The key has expired', 'A payment is still unknown after the provider’s idempotency retention ends. Why is a new charge request unsafe, and what should happen?'),
'A new or expired key may no longer deduplicate the original successful effect. Query using the saved provider reference and reconcile against provider reports; keep the intent blocked from a fresh automatic charge while uncertain. Escalate unresolved cases under an explicit operational policy. Local record retention and provider idempotency retention are different boundaries.',
('Timeout becomes failure', 'Bad code: on timeout mark payment failed; retry with random UUID. Show a double-charge timeline and repair it.'),
'Timeline: provider captures chargeA; response is lost; local code marks failed; retry creates chargeB. Repair with a durable stable payment intent/key, explicit unknown state, status query or same-key retry within provider scope, and conditional callback handling. Reconciliation confirms the final state. Never assume timeout proves no external effect.', [
('The charge request times out. What is known?', 'The outcome may be unknown.', 'No charge occurred.', 'The provider always rolled back.', 'A new key is always safe.', 'Missing response does not reveal whether the remote side committed.'),
('What must an idempotency key be bound to?', 'The same scoped intent and request parameters.', 'Any arbitrary future amount.', 'Only the browser tab color.', 'A new random key per retry.', 'Reusing a key for changed parameters must be rejected or treated as a new explicit intent.'),
('Why still reconcile when a provider supports idempotency?', 'Internal state and provider/settlement records can still disagree.', 'Idempotency means reconciliation is forbidden.', 'All callbacks arrive exactly once.', 'Ledger entries are optional for every product.', 'Remote identity reduces one failure class; missed updates and accounting differences remain.'),
('A late callback conflicts with a terminal success. What helps?', 'Validated conditional state transitions and deduplication.', 'Blindly overwrite by arrival order.', 'Delete the payment intent.', 'Generate another payment key.', 'Arrival order alone is not a safe payment state machine.')],
'''flowchart TD
  U["Pay intent and stable key"] --> I["Persist intent and request fingerprint"]
  I --> P["Provider call with same key"]
  P --> K["Known success or failure"]
  P --> X["Timeout: unknown"]
  X --> Q["Status lookup and reconciliation"]
  W["Authenticated callback"] --> S["Conditional local transition"]
  K --> S
  Q --> S
  S --> L["Ledger link and durable order event"]''', ['Create one payment intent', 'Bind amount and stable identity', 'Call provider and record reference', 'Treat a lost reply as unknown', 'Reconcile and transition safely', 'What if a key expires while the result is unknown?'], lab='retry')

add('28-wallet', 'Move wallet money without losing the trail', 12, '341–378', 5, '27 payments; 07 consistency', [
('Name the rule money must obey', 'A transfer must debit one account and credit another by the same amount in one currency. Reject spending unavailable funds.', 'Sending30 from a100-unit wallet leaves70 and adds30 to the receiver.', 'No money created. No money lost.'),
('Use a ledger and a balance view', 'Append entries that explain every change. A balance is a useful view, but it must agree with the ledger.', 'A refund is a new linked entry. Do not erase the old transfer.', 'Correct with a new entry.'),
('Make the local transfer atomic', 'When accounts share a database boundary, lock or version both balances and commit the entries together.', 'Debiting the sender and crashing before crediting the receiver loses money in the visible state.', 'Two sides. One commit boundary.'),
('Cross-shard transfers need a protocol', 'Separate databases cannot share a simple local transaction. Choose an explicit coordination or reserve/commit workflow.', 'Two independent writes with retries do not prove an atomic transfer.', 'A queue is transport, not an atomic commit.'),
('Replay must rebuild the same state', 'Event replay works only when the rules are deterministic and versioned. Fence old leaders and validate snapshots.', 'A replay rule that asks for today’s exchange rate changes yesterday’s outcome.', 'Same events. Same rules. Same state.')], [
'Define available balance, holds, currency, transfer limits, and whether negative balances are allowed. This exercise forbids them. Fixed minor-unit amounts avoid ordinary binary floating-point errors; currency precision and conversion need explicit rules.',
'A double-entry journal balances signed amounts within the defined currency/transaction boundary. Entry identity, account, transfer ID, and correction links provide auditability. Maintain a materialized balance for fast admission, but verify it against the journal and protect it with the same transaction.',
'For a single database, lock both accounts in deterministic order, find/create the unique transfer request, verify available funds, write both entries and balances, then commit. Serializable/version-based alternatives require explicit conflict handling. A separate dedup insert after moving funds leaves a crash gap.',
'For separate shards, explain 2PC with coordinator recovery and possible blocking, or a durable reservation/state-machine protocol with pending states and compensation semantics. A saga is not automatically an atomic transfer visible to everyone. Define what each user can observe during recovery.',
'Event-sourced processing needs an ordered durable command/event history, deterministic validation, fenced leadership, and snapshot positions. Consensus replicates a chosen history but does not make arbitrary external calls deterministic. Observe imbalance checks, held-funds age, rejected overdrafts, and recovery time.'
], '''### Contract
Transfer30 units between two wallets in one database. No negative available balance. A retry returns the original result.
### Size
The contention risk is many transfers touching one account. Total users alone does not size that critical section.
### Model
Transfer(request_id, from, to, amount, state), balanced journal entries, and protected balance rows.
### Flow
Lock both accounts in ID order → check request identity and funds → write debit/credit and balances → commit.
### Stress
Predict: two70-unit transfers race against a100-unit account.

The guarded transaction lets one succeed and rejects the other. Two stale balance reads would incorrectly approve both.
### Operate
Reconcile journal sums and materialized balances. Retry after a lost reply using the same request ID.
### Explain
This local transaction is a valid starting boundary. Sharding changes the correctness protocol, not just the connection string.''', [
'Transfer within one currency, forbid negative available balances, keep auditable balanced entries, and deduplicate retries. Start with one transactional database; explicitly discuss the cross-shard extension.',
'5,000 transfers/s, at least two account touches and two journal entries per transfer. Hot merchant accounts may serialize far more work than average users. Benchmark transaction contention and journal growth.',
'Account(id, currency, balance, held, version); Transfer(id, scoped_request_key, from, to, amount, state); JournalEntry(transfer, account, signed_minor_amount). Unique request and balanced-entry checks inside the commit boundary.',
'Validate ownership, currency, and amount. Lock accounts in stable order; find or create the request; verify funds; write both entries and balance updates; commit; return stored result. Publish downstream notifications through a local outbox.',
'Race two spends, lose the response after commit, and crash between proposed debit/credit steps. One transaction prevents partial visibility. With separate shards choose a documented protocol; independent retrying writes cannot claim atomicity.',
'Reconcile ledger entries with balance views, detect aged holds/pending transfers, monitor contention, and test restore/replay. Corrections append linked entries. Restrict privileged adjustments and avoid sensitive logs.',
'A local transaction keeps the proof short. Sharding increases coordination and recovery work. Event sourcing enables replay only with deterministic versioned rules and correct replicated history; it is not a substitute for those guarantees.'
], ('A same-currency wallet', 'Design wallet transfers at5,000 transfers/s. No negative available balance. Retried requests must not move funds twice. Keep an audit trail. Start with a local transaction, then explain what changes when sender and receiver live on different shards.'),
('A replay uses today’s rules', 'A recovery process replays transfers using the latest fee rate and current exchange rate. Why can balances change, and how should replay work?'),
'Historical effects must be reproducible. Store the already-decided fee/conversion amounts and rule version in committed events, or replay under the exact deterministic historical rules. External rates and wall-clock calls cannot silently affect old events. Snapshot state must identify the log position and code/data version; verify rebuilt totals against journal checks.',
('Debit now, credit later', 'Bad workflow: debit sender; publish queue event; consumer credits receiver. The database commit can succeed while publishing fails. Can this promise an atomic transfer? Repair the claim and design.'),
'It cannot claim atomic debit/credit across that gap. If accounts share a database, commit both with the journal and unique request in one transaction. If separated, use a durable coordinated protocol with reservations/pending states and recovery; an outbox preserves transfer intent but still does not make both databases one atomic boundary. State visibility and compensation limits.', [
('Two70-unit transfers race against100 available. What prevents both succeeding?', 'A shared guarded transaction or equivalent serializable admission rule.', 'Two independent cached balance reads.', 'Different random request IDs alone.', 'Sending both through any queue.', 'The funds check and debit need a concurrency boundary.'),
('How should an incorrect posted transfer be corrected?', 'Append authorized linked correction entries.', 'Silently edit old ledger amounts.', 'Delete its audit record.', 'Only change the UI balance.', 'A preserved history explains both the original action and its correction.'),
('Does an outbox make two separate account databases atomic?', 'No; it preserves intent but needs a transfer protocol.', 'Yes for every consumer.', 'Yes if the event is small.', 'Only when a CDN is added.', 'Reliable publication and atomic multi-database state are separate problems.'),
('What is needed for deterministic replay?', 'Committed historical facts and versioned rules without fresh external decisions.', 'Current exchange rates for all past events.', 'A random seed chosen on every run.', 'Only more memory.', 'Replay must reconstruct the original effects rather than decide new ones.')],
'''flowchart TD
  R["Transfer and stable request ID"] --> V["Validate ownership, currency, amount"]
  V --> L["Lock both accounts in stable order"]
  L --> F["Verify available funds"]
  F --> T["One transaction: debit, credit, journal"]
  T --> C["Commit stored outcome"]
  C --> O["Outbox for notifications"]
  T --> A["Audit and balance reconciliation"]''', ['State the money rule', 'Validate a stable transfer request', 'Guard funds against concurrent spends', 'Commit both sides and the journal', 'Reconcile and replay historical facts', 'What changes when accounts live on different shards?'], lab='reservation')

add('29-exchange', 'Match orders in a clear sequence', 13, '379–414', 5, '20 queue; 28 wallet', [
('Specify the matching rule', 'An order book groups buy and sell orders by price. This exercise uses price first, then accepted order sequence.', 'Two equal-price orders cannot both be first. Use the exchange sequence, not phone time.', 'Price first. Accepted sequence next.'),
('Keep one authority per book', 'A single ordered owner for one symbol makes matching easier to reason about. Many symbols can use different owners.', 'Two machines independently matching the same book may sell the same resting order twice.', 'One book. One fenced authority.'),
('Record before promising', 'Persist and replicate the accepted command sequence before the promised acknowledgment. Derive trades deterministically.', 'An in-memory match lost on failover cannot support a durable success promise.', 'Fast is useful only with an honest durability rule.'),
('Keep market data separate', 'Order acceptance and matching are the critical path. Public price updates can use a replayable feed with sequence numbers.', 'A viewer missing one feed packet should detect a gap and recover.', 'Trading state and viewing state differ.'),
('Recover without two active leaders', 'A standby replays the same committed commands. Failover fences the old owner and resumes from the correct position.', 'A partitioned old leader must not keep publishing valid trades.', 'Failover needs fencing, not just detection.')], [
'This is a simplified engineering exercise, not a trading system specification. Clarify limit orders, partial fills, cancel behavior, risk checks, and price-time priority. User/device timestamps are not a fair authoritative ordering source. A cancel racing a fill resolves by the accepted sequence.',
'A per-symbol book maintains price levels and FIFO queues at each price. Partitioning by symbol preserves a simple serial order. One very hot symbol remains a capacity limit; spreading it across independent matchers changes the matching protocol and fairness proof.',
'Durable admission, replicated log positions, deterministic matching, and trade IDs create a recoverable path. Risk reservations must prevent overcommit before acceptance. A success acknowledgment must identify whether it means received, durably accepted, or matched; those are different milestones.',
'A market-data publisher emits sequenced snapshots/deltas from committed state. Clients detect missing sequence ranges and obtain a snapshot plus tail. Backpressure or feed drops must not stop the matching loop. A book viewer may be stale while trading admission remains available under its own limits.',
'Standby recovery needs exact log position, deterministic code/data version, and leader epochs that downstream consumers enforce. Do not let two authorities produce valid effects. Measure durable-accept latency, match latency, queue age, feed gaps, and recovery time. Test cancel/fill races and failover after commit but before reply.'
], '''### Contract
One symbol accepts limit orders and cancellations. Price-time priority uses a server sequence. Accepted means durable, not immediately filled.
### Size
Measure the busiest symbol’s commands/s and latency. A thousand quiet symbols do not reveal one hot book’s limit.
### Model
Order(id, client_key, side, price_ticks, quantity, sequence, remaining). Price levels hold FIFO orders.
### Flow
Validate risk → assign sequence → commit replicated command → match deterministically → publish sequenced results.
### Stress
Predict: a cancel and a fill race.

Resolve by the accepted command sequence. A client timestamp cannot retroactively cancel an earlier committed fill.
### Operate
Standby replays committed history. Fence the old owner before accepting new authority.
### Explain
One serial book gives a clear ordering proof. Public feed delivery can scale separately.''', [
'Limit orders, partial fills, and cancellations for100 symbols. Price-time priority uses server accepted sequence. Durable acceptance is distinct from execution. Exclude complex order types and cross-venue routing.',
'100,000 commands/s total with60% on one symbol. The hot book receives60,000/s, so average1,000/s per symbol is misleading. Benchmark durable append and matching separately with tail latency.',
'Order(client_key, symbol, side, price_ticks, quantity, remaining, sequence); price-level FIFO queues; durable commands and trade IDs; reserved funds/positions; leader epoch. Use bounded integer ticks/units.',
'Authenticate and check limits, assign authoritative book sequence, durably replicate command under the acknowledgment contract, apply deterministic matching/cancel rules, record outputs, then publish executions and market-data deltas.',
'Race cancel/fill, duplicate a client command, crash after commit before reply, and partition the old leader. Replay committed commands once by stable identities. Fence stale authorities in storage/output paths. A cancel cannot erase an earlier fill.',
'Track durable-accept and match latency separately, hot-book queue age, feed gaps, standby lag, and recovery time. Rebuild from snapshot plus exact log tail; test state hashes. Apply backpressure/admission rather than silently dropping accepted orders.',
'Per-symbol serialization is simple and parallel across symbols. A hot symbol remains a bound. Batching can improve throughput but adds latency. Replication improves recoverability only when commit/election/fencing rules preserve one accepted history.'
], ('A simplified order-matching service', 'Design limit orders and cancellations for100 symbols at100,000 commands/s. One symbol gets60% of traffic. Use price-time priority. Explain durable acceptance, partial fills, cancel races, duplicate requests, market-data recovery, and fenced failover.'),
('A viewer misses feed messages', 'A market-data client sees sequence100 followed by105. How should it recover without affecting order matching?'),
'Detect the gap, stop claiming the local view is current, and request missing deltas if retained. Otherwise obtain a consistent snapshot at sequenceS plus all deltas afterS, buffering during synchronization. Use a separate replay/snapshot path with quotas so slow viewers cannot block matching. Execution and market-data delivery have different promises.',
('Two active matchers', 'Bad failover: after missing three heartbeats, start a new matcher; the old one may still send trades. Repair the authority rule.'),
'Use a coordinated leadership epoch/lease with enforced fencing in durable writes and effect publication. New authority resumes only from the committed sequence; downstream paths reject stale epochs. Heartbeat suspicion alone does not revoke an old process’s ability to write. Test a partition that isolates old/new leaders while both can reach some clients.', [
('Which time should break equal-price priority here?', 'The authoritative accepted command sequence.', 'The user phone clock.', 'Packet arrival time at any random replica.', 'The alphabetical username.', 'The server sequence provides a reproducible order under the chosen rule.'),
('Why is total throughput insufficient for sizing?', 'One symbol can dominate one serial book.', 'Every symbol always gets equal traffic.', 'Replication makes matching free.', 'The average is the peak.', 'Partition skew can leave one authority overloaded while others are idle.'),
('What should a feed client do after a sequence gap?', 'Recover missing deltas or a snapshot plus tail.', 'Pretend the next update contains everything.', 'Cancel every user order.', 'Restart the matching engine.', 'A missed incremental update can leave the local book wrong.'),
('What prevents an old matcher from emitting valid trades after failover?', 'Enforced authority epochs and fencing.', 'Heartbeat detection alone.', 'A new process name.', 'Only a larger CDN.', 'Failure suspicion is not the same as revoking write authority.')],
'''flowchart TD
  U["Client order and stable ID"] --> R["Validation and risk reservation"]
  R --> S["Authoritative book sequence"]
  S --> L["Replicated durable command log"]
  L --> M["One fenced deterministic matcher"]
  M --> E["Executions and order state"]
  M --> F["Sequenced public feed"]
  L --> B["Standby replay and failover"]
  B --> M''', ['Define price-time priority', 'Validate and reserve risk', 'Sequence and durably accept', 'Match with one fenced owner', 'Publish and recover sequenced views', 'What if a cancel and fill arrive together?'])

add('30-architecture-assessment', 'Prove the design transfers', 0, 'all chapters', 4, 'Volume 1 assessment; Volume 2 practice and delayed recall', [
('Use evidence, not chapter counts', 'Reading is progress. Independent design needs a stronger check. Solve a new prompt before opening any reference.', 'You can recognize a payment diagram but still miss the lost-reply case.', 'Show the reasoning you can retrieve.'),
('Pick the dominant risk', 'A familiar framework keeps the structure steady. Spend depth on the problem’s hardest promise.', 'Booking needs a concurrency proof. Metrics needs missing-data and cardinality rules.', 'Same structure. Different deepest question.'),
('Test a changed rule', 'After your design, change one requirement and explain what breaks. This checks understanding beyond a memorized picture.', 'What if a search result must disappear immediately instead of after one minute?', 'Change a constraint. Follow the consequences.'),
('Return after a delay', 'Repeat a different problem later without notes. Look for the same reasoning gaps across attempts.', 'A better answer tomorrow after copying is weaker evidence than a fresh answer next week.', 'Delayed retrieval shows what stayed.'),
('Connect it to real work', 'Choose one service you know. Trace a request, inspect a metric, and write one small reversible improvement.', 'An actual retry that can duplicate a job is a useful architecture review finding.', 'One real trace beats ten unexplained boxes.')], [
'The app reports separate evidence for explored lessons, submitted designs, quizzes, and delayed recall. None alone certifies seniority. AI feedback can miss errors; validate the main correctness argument with a timeline, counterexample, meaningful test, or peer review.',
'Use Contract → Size → Model → Flow → Stress → Operate → Explain. Explicitly name the single most important rule, the authority that enforces it, and the moment of durable acceptance. Remove components that do not serve a requirement.',
'Transfer exercises should change traffic skew, freshness, failure model, or access rules. Keep previous assumptions visible so you can identify the affected boundaries. A new box without a changed guarantee is not a complete adaptation.',
'Use the scheduled recall queue. A later good recall should explain a mechanism and a failure case, not reproduce exact wording. If you need the reference, label the attempt assisted and schedule another unaided attempt later. Honest partial recall is useful diagnostic data.',
'For work transfer, record observed behavior rather than claiming unseen tests passed. State a service objective, one risk, a small experiment, and a rollback condition. Avoid copying private production content into the AI tutor.'
], '''### Contract
A local library lends one remaining copy of a book. Two patrons request it together.
### Size
Ten requests/s is small, but the last-copy race still matters.
### Model
Inventory(book, available, version), Loan(request_id, patron, state).
### Flow
Guard availability and loan creation in one transaction. Return the stored result on retry.
### Stress
Predict both reads before either write. Then place the guarded transaction around the decision.
### Operate
Track failed/conflicting loans and expired holds.
### Explain
This uses the reservation mechanism in a different domain. That is transfer, not another architecture to memorize.''', [
'Find events nearby and sell exact seats. Search may lag30 seconds; no double sale; payments can be unknown. Define ownership, hold expiry, and what accepted/paid/confirmed each mean.',
'Assume5,000 searches/s,500 hold attempts/s, and a20x hot-show spike. Size hot-seat contention, provider quota, and spatial candidates separately. Estimate which path reaches a limit first.',
'Event/place spatial view; authoritative ShowSeat(show,seat,state,owner,expiry,version); Reservation(request_key,state); PaymentIntent; outbox. Search and seat authority are separate views.',
'Search cells then exact-filter event distance. Hold seats conditionally with request identity. Persist payment intent; call provider with stable key. Transition hold to confirmed only under valid state; publish notifications via outbox.',
'Race two buyers, expire a hold during payment, lose a provider reply, and return a stale search result. Use current authoritative checks, unknown payment state, reconciliation, and an explicit refund/re-reservation policy.',
'Monitor hold conflicts/age, provider unknown age, search lag, queue age, and confirmation correctness. Run a bounded hot-show load test, canary admission changes, and define rollback thresholds.',
'Explain one rejected alternative for each important decision: cache-only locking, new payment keys on retry, and global message order. State why each fails or adds cost under the contract.'
], ('Nearby events with scarce seats', 'Without notes, design nearby event discovery plus exact-seat checkout.5,000 searches/s;500 hold attempts/s with20x hot-show spikes. Search may lag30 seconds. Never sell a seat twice. Holds last five minutes. A payment may succeed after a lost reply. Explain the seven phases and trace the hardest race.'),
('Rebuild a usage dashboard', 'In a later session, design per-tenant API usage totals from100,000 events/s. Live totals may be revised for ten minutes. A monthly export must be reproducible. Handle duplicate delivery, one hot tenant, missing data, and a historical rebuild.'),
'Define stable event identity, trusted event time, lateness/correction boundaries, and tenant authorization. Keep raw retained facts and consistent checkpoints; publish versioned tenant/window results. Split hot keys into deduplicated partials. Finalize a versioned export with input ranges and rule versions. Backfill separately, compare, then switch. Monitor lag, missing partitions, duplicate rate, and reconciliation gaps. A watermark is not proof that every possible event arrived.',
('Review an unsafe failover', 'Architecture review: one leader updates wallet balances in memory, replies success, then sends events to a replica. After a heartbeat timeout a second leader starts. Both may write. List the broken promises and propose a minimal safe redesign.'),
'Success before durable replication can lose acknowledged transfers. Memory alone lacks a recoverable committed history. Heartbeat suspicion does not fence the old writer. Two authorities can overspend or fork balances. Start with a transactional durable ledger and protected balance updates plus stable request IDs; use an explicitly replicated commit/election protocol if failover is required. Fence stale epochs. Reconcile and test commit-before-reply, partition, and replay scenarios.', [
('Which is strongest evidence of learning?', 'A delayed unaided design that adapts to a changed constraint.', 'Opening every page once.', 'Copying a reference diagram immediately.', 'Counting technical words.', 'Retrieval and adaptation show more than familiarity.'),
('What should decide the deepest part of an HLD answer?', 'The hardest promise and likely failure for this problem.', 'The component you memorized most recently.', 'Always adding microservices.', 'Always global ordering.', 'The framework is stable, but the risk emphasis changes.'),
('An AI score is high. What still deserves validation?', 'The central correctness argument and failure timeline.', 'Nothing; scores prove production safety.', 'Only the diagram colors.', 'Only word count.', 'AI feedback is provisional and may miss an important counterexample.'),
('What is a useful first architecture task at work?', 'Trace one real request and propose a small measurable reversible improvement.', 'Replace every database at once.', 'Draw every tool logo from memory.', 'Copy private production secrets into chat.', 'A concrete trace connects design reasoning to observable behavior.')],
'''flowchart TD
  P["New prompt without notes"] --> C["Contract and dominant risk"]
  C --> S["Size, model, and request flow"]
  S --> T["Race, retry, and failure trace"]
  T --> O["Operations and trade-offs"]
  O --> F["Feedback then focused repair"]
  F --> D["Different prompt after a delay"]
  D --> W["Apply one decision at work"]''', ['Attempt without references', 'Name the hardest promise', 'Trace the safe mechanism', 'Change a constraint and repair', 'Return later and apply at work', 'Can you defend this design without its diagram?'])
MODULES[-1]['book'] = 'Original cross-chapter assessment. Applies Volume 2 mechanisms; no extra book chapter.'


def volume2_modules():
    modules = deepcopy(MODULES)
    def readable(value):
        if isinstance(value, str):
            return re.sub(r'(?<=[a-z])(?=\d)', ' ', value)
        if isinstance(value, list):
            return [readable(v) for v in value]
        if isinstance(value, dict):
            return {k: (v if k in {'id', 'track', 'code', 'lab'} else readable(v)) for k, v in value.items()}
        return value
    return readable(modules)


VOLUME2_SOURCES = '''\n\n## Volume 2 extension
Alex Xu and Sahn Lam, System Design Interview: An Insider’s Guide, Volume 2.
The supplied scanned PDF is the chapter reference. Printed page ranges appear on each module.
PDF page offsets are irregular; use chapter titles/printed numbers in the book.
All lesson wording, prompts, examples, answer reasoning, and diagrams in the extension are original teaching material.
The scan, book text, and book images are not bundled with the application.

The thirteen chapter families are covered in modules17–29. Module30 checks transfer across them.
The course extends the book with explicit retry boundaries, access checks, failure traces, and operational tests.
A reference is one defensible argument, not a required product list.

Primary references for deeper verification:
- [PostgreSQL row locks and deadlocks](https://www.postgresql.org/docs/current/explicit-locking.html): reservation/wallet transaction boundaries.
- [Apache Kafka design](https://kafka.apache.org/41/design/design/): partition logs, consumer positions, and delivery scopes.
- [Stripe idempotent requests](https://docs.stripe.com/api/idempotent_requests): provider-specific key parameters and retention. Other providers differ.
- [Google SRE monitoring](https://sre.google/sre-book/monitoring-distributed-systems/): user symptoms, signal choice, and alert noise.
- [Redis sorted sets](https://redis.io/docs/latest/develop/data-types/sorted-sets/): ordered score views.
- [PostGIS ST_DWithin](https://postgis.net/docs/ST_DWithin.html): indexed radius candidates and distance semantics.
- [Amazon S3 multipart upload](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html): upload lifecycle and completion.
'''
