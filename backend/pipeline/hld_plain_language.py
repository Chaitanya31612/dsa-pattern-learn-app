"""Short teaching cards. The full explanations remain available as optional depth."""
CARDS = {}


def cards(slug, title, rows):
    CARDS[slug] = {'title': title, 'rows': rows}


cards('00-design-framework', 'A simple way to solve any HLD question', [
 ('Agree on the problem', 'Ask what the user needs. Pick two or three features. Say what you are leaving out. Name the rule that must never break.', 'For a booking app: search and reserve a seat. Two people must not get the same seat.', 'Features first. Boxes later.'),
 ('Estimate what matters', 'Estimate the busy path. Keep the units visible. Use the number to make a decision.', 'Chat may have few messages but many open connections. Video needs enough network capacity for its bytes.', 'A number earns its place only if it changes a choice.'),
 ('Choose the data and rules', 'List what you store and how you find it. Pick the trusted copy. Say which changes must happen together.', 'A short link needs a code and a target. Only its owner can edit it. The same code must not point to two targets.', 'Data follows the questions you need to answer.'),
 ('Walk through one request', 'Follow one write and one read from start to finish. Say when you return success. Add a component only when it solves a named problem.', 'For chat: check access, save the message, say accepted, then try to deliver it.', 'Follow the arrow. Explain the work.'),
 ('Try to break it', 'Pick the two biggest risks. Use a small example: two users, one crash, one very busy item, or one old value.', 'Two people read “one seat left.” Both try to book. Where does the system choose one winner?', 'Two users and one crash reveal a lot.'),
 ('Keep it running', 'Choose a useful measurement. Explain what you do when it fails. Check access, cost, and how to release a change safely.', 'For background jobs, watch how long the oldest job has waited. Worker CPU alone does not tell the user’s story.', 'Measure what the user feels.'),
 ('Explain your choices', 'Say why you chose this design. Give an alternative and the cost of your choice. Name what you would check before building it.', '“A queue lets checkout finish quickly. Emails may arrive later. We need retries and a delay alert.”', 'Choice → reason → downside.'),
 ('Spend time on the real risk', 'Keep the same structure. Change the detail you focus on. Ask yourself what is hardest about this particular problem.', 'Bookings need careful updates. Video needs byte delivery. Chat needs saved messages and reconnects.', 'Same map. Different difficult turn.'),
])

cards('01-request-scale-estimation', 'Requests, load, and simple estimates', [
 ('Find where the request waits', 'A request travels through several steps. It may wait for a connection, database, or another service. Low CPU does not mean the request is fast.', 'A checkout takes three seconds because payment is slow. Adding CPU does not make payment reply faster.', 'Slow can mean waiting, not working.'),
 ('Keep a few useful formulas', 'Divide daily operations by 86,400 to get the average per second. Add a clear peak assumption. Multiply objects by their size to estimate bytes.', 'One million requests a day is about 12 per second. A five-times peak is about 60 per second.', 'Rate, bytes, and peak. Write the units.'),
 ('Scale the busy part', 'Find the shared limit before adding servers. More app servers can make the database busier. Fix the actual limit.', 'Ten servers wait for database connections. Fifty servers may create even more waiting.', 'More servers do not always mean more useful work.'),
 ('Connect the number to the choice', 'Explain what your estimate changes. Test the choice with real data and failures. Do not use one traffic number to choose every database.', 'Many reads may justify a cache. First check what is repeatedly read and what happens when the cache is empty.', 'Estimate → choice → check.'),
])

cards('02-data-cache-correctness', 'Store data safely and use caches wisely', [
 ('Start with reads and writes', 'List the questions the app asks its data. Choose keys and indexes to answer them. Decide which copy is trusted.', 'An order lookup uses order ID. A customer history page needs orders grouped by customer and date.', 'Choose storage from the work it must do.'),
 ('Keep an important update together', 'Two requests can run at the same time. An atomic update means the database makes one indivisible decision. A local lock does not protect other servers.', 'For the last seat, change available to held only if it is still available. Check whether your request won.', 'Check and change together.'),
 ('A cache is a shortcut', 'A cache holds a reusable copy. It can be old or disappear. Say how old it may be and how you protect the database when it is gone.', 'An old reader may fill the cache after an update deleted it. Deleting a key is not a complete freshness plan.', 'Fast copy. Trusted source. Clear freshness rule.'),
 ('Watch and recover', 'Check slow queries, failed updates, and old cache values. Test losing the cache. Test restoring saved data, not just making copies.', 'A bad delete may spread to every replica. A tested backup helps recover the earlier data.', 'Copies help failure. Backups help recovery.'),
])

cards('03-url-shortener', 'Short links: create, redirect, and update', [
 ('Decide what a link promises', 'A short code points to a target. Ask who can edit it, when it expires, and how quickly removal must take effect.', 'A five-year permanent link and a link you can revoke in two seconds need different cache rules.', 'Changing the promise changes the design.'),
 ('Create a code safely', 'Random codes can collide. Let the trusted store reject duplicates and try another code. Encoding a number does not make it secret.', 'Two servers choose the same code. A unique database key picks one winner.', 'Random reduces collisions. A unique key handles them.'),
 ('Make the read path fast', 'Repeated link visits can use a cache. A very popular link can be a special problem. Plan for an empty cache at the busy hour.', 'Most requests hit the cache. When it fails, the database suddenly sees all those requests.', 'Design the miss path too.'),
 ('Keep old links working', 'Change generators and storage carefully. Preserve existing mappings. Check that owners can manage only their own links.', 'A new code format is fine if the redirect service still understands the old codes.', 'New format. Old links still work.'),
])

cards('04-unique-ids', 'Make unique IDs without hidden assumptions', [
 ('Unique and ordered are different', 'Unique means two records do not share an ID. Time-sortable means IDs roughly follow time. Strict global order needs a stronger shared decision.', 'Two machines may have different clocks. Their timestamp order may not match the order events actually happened.', 'Unique is not the same as ordered.'),
 ('Build the ID from parts', 'A time-based ID can contain time, worker number, and a counter. Each active worker needs its own number. The counter must not wrap in the same time slot.', 'With 12 counter bits, one worker has 4,096 counter values in a millisecond.', 'Different worker. Safe time. No counter wrap.'),
 ('Handle a clock going backwards', 'Clocks can move backwards. A restart can also repeat old state. Choose whether to wait, stop, or use another safe scheme.', 'A worker already used time 100. Its clock now says 99. Reusing old ID parts may repeat an ID.', 'A clock is an input, not a promise.'),
 ('Check the assumptions in production', 'Watch duplicate rejections and clock problems. Plan safe worker ownership and restarts. Avoid stronger guarantees than you need.', 'A random ID with a separate created-at field may be enough if strict ordering is not needed.', 'Choose the smallest useful guarantee.'),
])

cards('05-rate-limiter', 'Decide which requests may enter', [
 ('Define what the limit means', '“100 per minute” is incomplete. Is it any 60 seconds, a calendar minute, or a refill rate that allows bursts?', 'A token bucket can allow a small burst. An exact rolling-window limit counts accepted requests in the recent interval.', 'Define the limit before the algorithm.'),
 ('Make one shared decision', 'Checking and spending a token must happen together. Every app instance must use the same rule and shared state, or safe assigned shares.', 'There is one token left. Two servers must not both spend it.', 'Check and spend in one step.'),
 ('Choose behavior during failure', 'If the limit store fails, allowing everything may overload the service. Rejecting everything may stop useful work. Choose the policy for each operation.', 'A low-risk read may get a small emergency budget. A protected write may need to wait or be rejected.', 'Failure behavior is part of the product.'),
 ('Measure protection, not just rejection', 'Watch checker errors, delays, and the service you protect. Slow requests may also need a limit on work already in progress.', 'Legal arrivals still overwhelm a provider if every call takes 30 seconds.', 'Limit arrivals and watch ongoing work.'),
])

cards('06-consistent-hashing', 'Place keys and move data safely', [
 ('Use a stable placement map', 'A key maps to a server. A hash ring can move a smaller group of keys when servers change. It does not copy data itself.', 'Add a server between A and B. Only keys in the new ownership interval move to it.', 'Placement is a map, not a moving truck.'),
 ('Keep replicas on different machines', 'Virtual positions help spread keys. They are not extra physical servers. Keep important copies in different failure areas.', 'Three virtual positions on one machine all disappear when that machine fails.', 'Three positions are not three safe copies.'),
 ('Move while writes continue', 'Copy old data, catch up new writes, check the result, then change ownership safely. Keep a rollback window.', 'Deleting the old shard before new writes arrive at the new owner can lose data.', 'Copy → catch up → check → switch.'),
 ('Treat a hot key separately', 'One popular key can overload its owner. More virtual positions do not automatically divide that key’s work.', 'One celebrity profile gets half the reads. Replicated reads or coalescing may help more than another ring position.', 'Balanced keys can still mean unbalanced traffic.'),
])

cards('07-key-value-store', 'Store values across machines', [
 ('Say what a read must see', 'A key retrieves a value. Decide whether reads may be old and whether a user must see their own update. Stronger rules change failure behavior.', 'A profile can briefly show an old photo. Selling the last seat needs a stronger update rule.', 'Choose the promise before the replicas.'),
 ('Save before saying saved', 'Memory can disappear. Record writes durably under a clear policy. Explain which copies must confirm before success.', 'A server returns success, then loses power. If the value was only in memory, it may be gone.', 'Saved means a defined durable boundary.'),
 ('Do not overpromise from replica counts', 'Read and write groups can overlap. You still need rules for versions, competing writes, and changing owners. Overlap alone is not a whole protocol.', 'Two writers change the same value. Which version does a reader return, and why?', 'Replica math is one part of the proof.'),
 ('Repair differences deliberately', 'Copies may disagree after failures. Detect differences and choose a clear merge or conflict rule. Test restoring backups too.', 'Two devices edit a preference offline. The app may ask for a choice instead of silently losing one edit.', 'Detect the conflict. Decide its meaning.'),
])

cards('08-notifications', 'Background work that survives retries', [
 ('Name each stage of success', 'Accepted, queued, sent to a provider, and delivered are different. A timeout may mean the result is unknown. Avoid saying exactly once without a clear boundary.', 'An email provider accepted the send, but its reply was lost. Sending again may make a duplicate.', 'No reply does not mean no effect.'),
 ('Save the work you intend to do', 'Save the business change and its pending event together. A dispatcher sends it later. Repeated dispatch still needs safe handling.', 'An order saves successfully, then the process crashes before publishing its email event. A saved outbox preserves that intent.', 'Save the intent before dispatch.'),
 ('A queue buys time', 'A queue handles a short burst. It cannot fix a permanent capacity shortage. Limit retries and respect provider quotas.', '300 sends arrive each second. The provider allows 200. The queue grows by about 100 each second.', 'Arrival must eventually fit processing.'),
 ('Watch delay and recover stuck work', 'Watch the oldest waiting job. Keep failed jobs for investigation and safe replay. Use stable IDs to recognize retries.', 'Workers look healthy, but receipts are two hours late. Queue age shows the user problem.', 'Watch waiting time, not just busy machines.'),
])

cards('09-web-crawler', 'Fetch pages without losing control', [
 ('Choose eligible work', 'A crawler discovers more work as it runs. Set limits on sites, depth, size, and retries. Schedule by host so many workers still respect its rate.', 'Adding 100 workers must not turn a host’s one-request-per-second policy into 100 requests per second.', 'More workers. Same host rule.'),
 ('URLs and content are different', 'Two URLs may lead to the same content. Similar-looking URLs may lead to different content. Track URL tasks and content fingerprints separately.', 'Removing every query parameter may merge two different product pages.', 'Same URL? Same body? Ask both.'),
 ('Give work a recoverable state', 'Record discovered, claimed, completed, and retryable work. A crash should not strand a page forever.', 'A worker marks a URL visited, then crashes before downloading. A boolean alone cannot show what is still missing.', 'Discovered is not completed.'),
 ('Check where the server really fetches', 'A public URL can redirect to a private destination. Check resolved addresses and redirects. Bound bytes and time.', 'A submitted link redirects to an internal service. Checking only the original text misses the real destination.', 'Check every destination, not just the first.'),
 ('Measure the slow stage', 'Fetch, parse, and store have different limits. Watch host delay and useful content, not only queue size.', 'A parser can be slow even when downloaders are idle. Add capacity where the time is spent.', 'Measure each stage before scaling it.'),
])

cards('10-news-feed', 'Build a feed without copying the whole world', [
 ('Posts and feeds are different', 'The post is the trusted content. A feed is a prepared list of references. Decide ordering, freshness, and access.', 'A feed still lists a private post after access changes. Listing it does not mean the viewer may read it.', 'Prepared list is not permission.'),
 ('Count the extra work', 'One post can create work for many followers. Push makes reads cheaper. Pull saves publishing work. A mix can handle very large authors.', 'A celebrity has ten million followers. Updating all their feeds is not one small write.', 'One post can mean millions of updates.'),
 ('Trace publish and read separately', 'Save the post, update feed lists safely, then read and check current access. Say how paging behaves when new items arrive.', 'Offset page two can shift after new posts. A cursor helps if its ordering and paging rules are clear.', 'Source → prepared list → allowed page.'),
 ('Rebuild what is derived', 'Feed lists can be rebuilt when source data is kept. Watch how far behind they are. Keep deletion and access rules separate from display freshness.', 'A 30-second feed delay is okay. A 30-second private-content leak may not be.', 'Freshness and privacy have different clocks.'),
])

cards('11-chat', 'Chat that still works after reconnecting', [
 ('Explain what sent means', 'Accepted means saved under your policy. Delivered means a device confirmed receipt. Read means something else again.', 'The sender gets accepted while the recipient is offline. The message is saved but not delivered yet.', 'Accepted ≠ delivered ≠ read.'),
 ('Keep messages separate from connections', 'Connections help route live traffic. Saved history is the trusted record. Use stable request IDs and a clear conversation order.', 'A gateway restarts and loses sockets. The messages should still exist in history.', 'Socket is the road. History is the record.'),
 ('Recover uncertain sends and missed delivery', 'Retries reuse the same logical request ID. Reconnecting devices fetch after their last safe cursor. Clients can recognize repeated messages.', 'The message saved, but the reply was lost. Retrying with the same ID returns that message instead of creating another.', 'Same action. Same ID. Same logical message.'),
 ('Online status is approximate', 'Heartbeats suggest a device is alive. Missing heartbeats eventually mark it offline. Large groups also multiply delivery work.', 'A laptop loses power. The server cannot know instantly; it waits for the heartbeat to expire.', 'No heartbeat is a clue, not instant truth.'),
 ('Plan for slow devices and reconnects', 'Bound buffers. Watch delivery delay and reconnect bursts. Check membership on messages and history.', 'A slow phone cannot receive unlimited buffered messages. Disconnect and catch up from history when needed.', 'Bound the buffer. Keep the history.'),
])

cards('12-autocomplete', 'Fast suggestions while someone types', [
 ('Decide which suggestions count', 'Prefix matching, spelling correction, and personal results are different jobs. Choose the one you need and define freshness and privacy.', 'Global popular words and a private employee directory must not share one public answer cache.', 'Matching rule first. Index second.'),
 ('Prepare results before the request', 'Collect eligible data, rank it, and build a prefix index. Keep a small list of best results for common prefixes when useful.', 'For “ca,” the server can return a prepared top five instead of scanning every word starting with “ca.”', 'Do work once. Reuse it on reads.'),
 ('Publish a complete new version', 'Build and check a new index before switching readers to it. Keep fast removal rules for results that must disappear sooner.', 'Popularity may update hourly. A blocked private term may need removal in five seconds.', 'Build → check → switch. Urgent removal takes its own path.'),
 ('Ignore answers to old input', 'Responses can arrive in the wrong order. Show only the response for the current typed input. Watch index age and serving delay.', '“ca” is slow. “cat” returns first. The late “ca” answer must not replace the current suggestions.', 'Latest input wins the screen.'),
])

cards('13-video-platform', 'Upload, prepare, and play video', [
 ('Separate big bytes from small decisions', 'The app handles access and status. Object storage carries large files. Start with upload and playback; add other features only when needed.', 'The API authorizes an upload. A scoped URL lets the client send bytes directly to storage.', 'API handles permission. Storage handles bytes.'),
 ('Ready means usable', 'Upload and check the source. Prepare the required video versions. Publish a ready manifest only after those outputs are checked.', 'A transcoder starts but crashes halfway. The video must not appear ready just because work started.', 'Upload → check → prepare → publish.'),
 ('Estimate delivery bytes', 'Use viewer count and average bitrate to estimate network load. API calls alone do not size playback.', '50,000 viewers at 3 Mb/s need about 150 Gb/s before extra overhead.', 'Viewers × bitrate = delivery load.'),
 ('Keep retries and private access safe', 'Use stable output versions. Avoid overwriting a currently served video during a retry. Check cache and URL lifetimes against access rules.', 'A private link stays usable for a day. That may break a promise to revoke access in five seconds.', 'A fast cache still has to obey permission.'),
])

cards('14-file-sync', 'Sync files without silently losing edits', [
 ('Give a file a stable identity', 'The file is more than its path. Keep identity, name, parent folder, access, and version separately.', 'Renaming a file should not make every device think it is unrelated new content.', 'Name can change. Identity stays.'),
 ('Check the version before replacing it', 'Upload bytes first. Then publish the new version only if the old version still matches. A conflicting edit needs an explicit response.', 'Two offline devices edit version 3. After one publishes version 4, the other must not silently overwrite it.', 'Compare the base before replacing.'),
 ('Chunks help reuse and resume', 'Large files can be split into pieces. Upload only missing pieces and verify them. Deduplication needs privacy and integrity rules.', 'Changing one part of a large file may reuse unchanged chunks rather than upload everything.', 'Reuse safe pieces. Verify the whole version.'),
 ('Catch up from a saved change list', 'Notifications may be lost. Devices read changes after a cursor. Keep deletes as versioned changes so stale devices cannot quietly undo them.', 'A phone comes online after a week. It asks for missed changes instead of trusting old notifications.', 'Notification says look. Change log says what changed.'),
 ('Clean only what is truly unused', 'Old versions and active uploads may still refer to chunks. Check references before deletion. Test conflict and restore paths.', 'A cleanup job removes a chunk still used by yesterday’s retained version. That version can no longer be restored.', 'Unused means unreferenced, not merely old.'),
])

cards('15-production-architecture', 'Run it, protect it, and change it safely', [
 ('Measure useful success', 'Pick what users actually need. An SLI is the measurement; an SLO is the target. Explain new terms instead of collecting them.', 'A job service is up, but jobs never finish. Completion time shows the problem better than uptime.', 'Measure the promise.'),
 ('Bound the damage', 'Limit waits, retries, and work in progress. Keep one failing dependency from consuming every resource. Test how much data and time recovery may lose.', 'A slow provider triggers endless retries. More requests make recovery harder.', 'Retry with a budget, not forever.'),
 ('Check who may do what', 'Login identifies the user. Authorization checks their right to this resource. Follow private data across every service and cache.', 'A logged-in employee must not read another tenant’s documents.', 'Known user is not automatic permission.'),
 ('Change in safe stages', 'Add a compatible new form. Move data and check it. Switch gradually. Remove the old form only after the rollback window.', 'New and old app instances run together. Both must understand data written during that period.', 'Expand → move → check → switch → remove.'),
 ('Write a decision someone can challenge', 'State facts, unknowns, alternatives, and the reason for your choice. Add a test and rollback plan.', '“The database may be the limit. Query and pool-wait measurements will confirm or reject that guess.”', 'Evidence beats confident guessing.'),
])

cards('16-final-assessment', 'Show you can use the ideas on a new problem', [
 ('Start from a blank page', 'Choose the right mechanisms for a new product. Use the same structure from memory. Do not compare with a solution until you save your attempt.', 'An artifact registry reuses storage and access ideas, but its revocation and byte-delivery needs differ from short links.', 'Learn the reason, not the picture.'),
 ('Handle one changed rule', 'The interviewer changes a requirement. Explain which choice changes and which parts still work.', 'A public cache is useful. Five-second access revocation may require a different serving policy.', 'Change the promise. Recheck the mechanism.'),
 ('Use evidence to score', 'Show the reasoning behind each score. A broken central rule blocks a pass. Good MCQs alone do not prove independent design.', 'A design gets many details right but double-books a slot. That issue still needs repair.', 'A good total cannot hide a broken rule.'),
 ('Keep the skill active', 'Use short delayed reviews and occasional new problems. At work, apply the same map to a real change.', 'Forget a product setting? Look it up. Keep the habit of checking data, flows, failures, and trade-offs.', 'Recall the map. Look up the small details.'),
])
