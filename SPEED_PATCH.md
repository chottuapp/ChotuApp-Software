# Speed S1: pacing-only update

The user diagnostic identified installed R10 SHA256 prefix `372afddb37e13f83`.
Elite Cosmetics showed 689 logged HTTP 200 responses with a mean of 0.42 seconds,
and no displayed rate-limit waits. API and image checks each used a 1.5-second
pacing floor. This patch targets that overhead without replacing application
source with a different version.

`install_speed_patch.py` changes only five adaptive-pacing constants in R10 from
1.5 to 0.35 seconds. An AST comparison rejects all other behavior changes. It
backs up the exact installed source and writes atomically. Repeating it is safe.
Price/image/variant checks, ordering, source freshness and output logic stay as
installed. Retry-After, 429/503 backoff and adaptive slowdown remain intact.

Finish the current fetch and close the app before applying. The running process
is not modified or stopped by this tool; the patch applies at the next launch.
Use `--dry-run` for a read-only source check. Default target is the existing
Desktop/ChotuApp_Software installation; --target supports custom paths.

Validation: exact R10 source and patched source exported identical values in every
workbook sheet from a fixed local HTTP catalog, including product prices,
variant availability, gallery images, categories, descriptions and top-seller
order. Timing was 10.54 seconds versus 2.48 seconds in that controlled run.
This is not a guaranteed speedup on real websites; source latency and throttling
can differ. A targeted test verifies Retry-After and rate-limit slowdown.

After installation, title remains R10. Run diagnose_speed.py to confirm a 0.35s
baseline and collect post-patch timings. Do not rerun a completed fetch solely to
benchmark against live data: source prices/stock can change between runs.
