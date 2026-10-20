# Saved fetch recovery

The approved cloud roots in `recovery-release.json` are the current LAAM and
Sapphire runs. Their existing checkpoint continuations retry temporary cooldowns
and time-budget expiry, up to the original six-run limit and no-progress guard.
The reviewed recovery workflow handles failed/blocked parser runs only when the
tested main commit differs from the failed run. It follows descendants of the
approved roots; it never starts a fresh catalog, interrupts active work, or
restarts a manually stopped, cancelled or successful run. Completed stores and
checkpoint identity are verified before dispatch. Cloud artifact expiry still
limits available recovery.

The Windows `watch_khaadi_recovery_windows.py` supervisor watches an existing
local fetch without taking over its worker lock. Once it exits, temporary curl
connectivity and source-cooldown errors retry after 1–15 minutes. Other failures
wait for a newly published worker release. Supervisor lifetime is 24 hours;
Ctrl+C stops supervision. On Windows it requests that automatic system sleep
be suppressed while supervision is active; shutdown/closing the laptop still
stops local processing. No startup task or background service is installed.

For a Khaadi parser repair, test the changed source, commit it, update the local
fetch launcher's pinned `REVISION` and file SHA256s, and commit the launcher.
Then update `khaadi_worker.commit` to that full launcher commit and
`khaadi_worker.sha256` to the launcher's SHA256 in `recovery-release.json`.
Publish the descriptor only after tests pass. The running supervisor checks this
feed over verified HTTPS, downloads only the fixed worker path from a full
commit ID, verifies its SHA256 and launches it after the previous worker exits.
It cannot rewrite parser rules or infer missing source facts.

Publishing the descriptor also triggers cloud recovery tests. Workflow-completion
and manual dispatch are supported as well. Failures retain logs and checkpoints;
no workbook is automatically uploaded to Drive or labeled as fully verified.

The updated Windows Khaadi supervisor publishes a limited heartbeat every 60 seconds to `local-run-status:local/khaadi.json`, using the PC's existing authenticated GitHub CLI. It sends only store identity, status, worker-lock activity, last progress event/age, check time and bounded source error; never the local workbook, cookies, tokens, configuration or process ID. Reporting failures do not stop fetching. The cloud combined reporter labels local telemetry older than three minutes unknown/stale. One local restart of the updated supervisor is necessary to install this capability; there is no remote-control service for an offline PC. Published pinned/hash-verified worker repairs are applied only after the existing worker exits; unknown source schemas still require a tested code repair.

## Reliability changes, 21 October 2026

LAAM stores persistent failed-product cooldowns in `laam-parsed.sqlite3`, alongside verified product and exclusion caches. Individual HTTP 500/502/504 product responses are deferred without two minute-long immediate retries per URL. After five consecutive failures, a fresh previously verified product URL is used to distinguish a healthy product service with broken individual URLs from a general outage. A failed health check pauses the source. Cooling URLs remain explicitly incomplete, are not marked sold out, and do not disappear from coverage accounting. They become eligible for verification after one hour. Parsed/excluded and deferred-queue counts contribute to checkpoint progress. No final complete-catalog claim or guessed product is emitted while unresolved pages remain.

Fresh Rule 804 live snapshots dispatch the cloud Drive-sync workflow immediately after changed reviewed artifacts are published. This complements completion events, manual repair dispatch and scheduled checks. Updated steps apply to newly started/resumed workflow jobs; existing healthy jobs retain their checked-out workflow until their next checkpoint continuation. Drive records scanning/finished/failed states and retains verification history when an upload fails. The target remains the owner-selected fixed folder, with same-name replacement and unmatched old stores preserved.

Unknown parser/price/stock conflicts require a tested adapter repair, not automatically generated code. Normal retry/cooldown/checkpoint continuation remains bounded and respects explicit stop, cancellation, source access restrictions, no-progress guards and continuation budgets. GitHub and Google Drive quotas, revoked credentials and source outages are reported; they cannot be corrected by inventing data or silently bypassing limits.

Khaadi's fresh cloud public-page check still redirects to a foreign storefront. Keeping local data and prices correct requires the Pakistan source. PC-independent Khaadi fetching needs a Pakistan-hosted runner/server or a source-approved public feed. A stopped/offline Windows process cannot be remotely started by GitHub status reporting; its heartbeat is explicitly stale/unknown until the local supervisor runs again.
