Controlled Fast Fetch

Two worker threads preload the same collection products.json pages, product.js prices and original product HTML pages that the canonical pipeline uses. The canonical pipeline then processes durable cached responses, preserving its price validation, variants, availability, descriptions, hero image selection, category mapping, best-selling order, audits and workbook layout.

Every fresh store has a new Saved Runs cache. Continue reuses only that interrupted run's saved snapshot. Old-day snapshots are not used for a new daily run. Successful responses are saved immediately to SQLite; failed responses are not substituted for valid data. Each worker owns its requests session and SQLite connections; extraction writes remain serial. No workbooks are written by preload threads.

There are at most two outstanding tasks. All new requests for the store share a 0.25-second minimum start interval (not two independent bursts). HTTP 429/503 stops further parallel task submission, increases shared pacing and honors Retry-After/cooldown. The canonical worker retries deferred requests using existing validation/backoff rules. Existing optional category/audit failure behavior remains unchanged; failures can still require REVIEW.

The existing 0.35-second baseline-only patch is applied by the installer as well. The parallel path requires Saved Runs; without its per-run durable paths the existing serial pipeline remains available. Stylo's prior rate-limit shortcut remains unchanged.

The target is substantially less idle time and overlapped network work. Fifteen minutes cannot be guaranteed: product count, HTML size, latency, errors, site throttling and local disk affect total time. Fixed-data equality and rate-limit tests do not prove every live website remains identical across requests; sites can change while any run is active.

Close the app before install_fast_fetch.py. The installer backs up program files and adds runtime hooks; it does not replace the extraction engine or delete settings, exports, templates or saved runs. Continue an incomplete run to retain completed stores. Log lines beginning FAST FETCH report preload progress. The complete source ZIP includes this module and hook.
