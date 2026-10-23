# User operating preferences — 21 October 2026

When asked whether files/runners are running, first read current GitHub cloud reports directly. Give the checked timestamp, active/queued count, completed store count, current errors, stale/unknown evidence and verified Drive count. Do not give a Windows CMD by default when cloud evidence is obtainable. Local Khaadi cannot be observed by cloud tools without a separate local reporter; do not infer that it is running from old status files.

The combined status workflow reads snapshots approximately every five minutes and on workflow completion. GitHub scheduling may delay it; this is not every-second telemetry or a promise that a chat agent remains online between turns.

For cleanup, remove only identified disposable generated caches. Preserve source code, tests, source fixtures, uploaded evidence, Excel files, credentials, Rule 804 records, audit/provenance data, checkpoints and backups unless specific evidence and user authorization support their removal. Do not delete unknown files merely because they appear unused.

Drive destination override: all future fresh-batch Rule 804 outputs go to `ChotuApp 19-10-2026 11-36AM`. Replace matching filenames and retain other stores. This supersedes the daily-folder instruction.


22 October 2026 monitoring update: use `catalog-tools/live_status.py` for status requests; it reads the Android report directly and verifies recent fetch-run terminal/active state using public GitHub pages. Snapshot task counts keep original timestamps. No second-by-second or always-online assistant monitoring is claimed.
Studio1.5 adds a native reporting thread before engine startup and after worker exit, plus a network-constrained persisted Android JobScheduler fallback (15-minute minimum, system-delayed). Active reporting targets30seconds. The phone must install/open the update once and have a valid GitHub connection. Missing credentials, force-stop, offline operation and Android restrictions cannot be bypassed by cloud code; missing or stale phone status stays unknown. Never ask for screenshots before first reading available cloud reports.

## 23 October: mobile is unavailable

Owner explicitly says to assume no mobile device. Do not ask for phone logs, app installation, token entry, or a phone heartbeat as the next step. Use cloud diagnostics and `catalog-tools/live_status.py` directly. Khaadi cloud attempt 39903597412 proved an HTTP 302 from pk.khaadi.com to us.khaadi.com, whose product JSON-LD uses USD; this is an actual Pakistan-source hosting/region blocker, not missing phone telemetry. Never call that a running Khaadi fetch or export foreign currency as PKR. A verified Pakistan-hosted worker or approved public Pakistan source is needed if the normal PK source remains unavailable to GitHub. A cloud-only gated fresh-start controller and Khaadi audit/Drive scope are ready; other stores must not be reset.
