Controlled Fast Fetch

Two worker threads preload the same collection products.json pages, product.js prices and original product HTML pages that the canonical pipeline uses. The canonical pipeline then processes durable cached responses, preserving its price validation, variants, availability, descriptions, hero image selection, category mapping, best-selling order, audits and workbook layout.

Every fresh store has a new Saved Runs cache. Continue reuses only that interrupted run's saved snapshot. Old-day snapshots are not used for a new daily run. Successful responses are saved immediately to SQLite; failed responses are not substituted for valid data. Each worker owns its requests session and SQLite connections; extraction writes remain serial. No workbooks are written by preload threads.

There are at most two outstanding tasks. New requests share a gate: a 0.25-second baseline for unthrottled sources, a conservative 1-second floor for Elite Cosmetics, and a persisted learned floor after throttling. HTTP 429/503 stops new requests for that store, preserves checkpoints, and records a cooldown of at least 60 seconds or the longer Retry-After. There is no 12/24/48-second repeated retry loop against a store already blocked in that run. Other selected stores can proceed. Continue Saved Run after cooldown retries the unfinished source; if the website still blocks, the saved work remains and the store is deferred again. Canonical validation still handles non-rate failures and may require REVIEW.

The existing 0.35-second baseline-only patch is applied by the installer as well. The parallel path requires Saved Runs; without its per-run durable paths the existing serial pipeline remains available. Stylo's prior rate-limit shortcut remains unchanged.

The target is substantially less idle time and overlapped network work. Fifteen minutes cannot be guaranteed: product count, HTML size, latency, errors, site throttling and local disk affect total time. Fixed-data equality and rate-limit tests do not prove every live website remains identical across requests; sites can change while any run is active.

Close the app before install_fast_fetch.py. The installer backs up program files and adds runtime hooks; it does not replace the extraction engine or delete settings, exports, templates or saved runs. Continue an incomplete run to retain completed stores. Log lines beginning FAST FETCH report preload progress. The complete source ZIP includes this module and hook.

Source cooldown and learned spacing are local metadata under source_pacing/. Restarting the app does not reset a still-active cooldown. A blocked category/product preload cannot be silently published as a complete catalog. This is a reliability improvement under throttling, not a claim that blocked sources can be fetched faster.
