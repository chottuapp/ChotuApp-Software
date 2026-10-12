# Durable selected-store runs

Install with the existing application closed. The additive installer inserts a
startup hook and adds resume_support.py; existing extraction functions and speed
constants are preserved. It makes a verified backup before writing.

Two new fixed buttons:

- New Fresh Run (selected): snapshot the selected stores and template; start a
  new empty cache and queue. Older saved runs are preserved on disk but the
  latest fresh run becomes the one available to Continue.
- Continue Saved Run: restore the last saved selection and template snapshot,
  skip completed stores with unchanged output files, and resume pending stores
  from successful saved API/page responses. The current checkboxes do not
  replace the saved queue.

State and responses are saved under saved_runs beside main.py. SQLite FULL
synchronous transactions persist committed responses and progress. Interrupted
HTTP requests, HTTP failures, malformed JSON and known challenge pages are not
saved as successful data. An in-flight request may need repeating after shutdown.
Rows/workbooks are reconstructed from saved responses; this is not restoration
of Python memory or an exact CPU instruction. Source pricing/stock from the old
run can be reused on Continue; use Fresh for an entirely new source snapshot.

Completed outputs retain their original IDs/data. Existing REVIEW flags remain
reviewed/unverified, never upgraded to approved FINAL merely by resuming. A
process lock prevents two app instances writing the queue simultaneously.

New persistence applies to runs started after this update. Previously interrupted
runs without a saved queue cannot be reconstructed safely. No process is killed
by the installer, and old Excel/checkpoint/backup files are not deleted.

Validation covered: selected queues and successful responses across process
restart; committed state after abrupt process exit; failed/malformed response
exclusion; fresh-run isolation; simultaneous-writer exclusion; GUI restart with
saved selection, cached response replay and completed-store skipping; visibility
of both buttons at 900x640. Real Windows shutdown/hardware validation remains
pending. The update does not claim to resolve the separate touchpad issue.

Immediate file status: each completed store publishes its Excel to the existing
ANAS_DATA_FETCH folder before the next store completes. The log prints FILE SAVED
NOW and the fixed control row shows Files saved: X/Y during the queue. A test
blocked the last store and verified the earlier file already existed on disk
and its completed state/count were persisted.

Resume replay speed: cached product-page responses bypass Image pacing only.
Cached pages still run the same hero/specification parsing and checks. All real
HTTP pacing, Pause, Retry-After and 429/503 waits stay unchanged. The test verified
a saved hero page was processed in under one second despite a 2.7s adaptive pace.
This removes replay overhead, not the source website rate limit.

UI responsiveness update: saved-run status uses an in-memory snapshot rather than waiting for the worker database lock. Event processing yields after 40 messages or 20 ms; unchanged counters are not redrawn. Durable worker writes, extraction rules and prices are unchanged. Windows hardware responsiveness still needs user verification.
