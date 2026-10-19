# Five websites per GitHub runner

`cloud-fetch-groups.yml` dispatches independent `cloud-fetch.yml` workflow runs with at most five distinct websites each. The registered 29 stores need six fresh groups (5+5+5+5+5+4). Each runner keeps the existing two-store processing limit, its own artifact set, source pacing, and bounded checkpoint continuation chain. GitHub account capacity determines how many dispatched jobs actually run simultaneously.

A `runner_group` concurrency key is retained through automatic continuation. Legacy runs keep the original global concurrency key. The dispatcher refuses to overlap an unrelated active fetch, rejects duplicate websites including www aliases, and records a downloadable group map. Re-running the same dispatcher does not dispatch its existing groups again.

For migration, save/stop the current legacy run first. The Windows helper `catalog-tools/start_five_store_runners_windows.py` finds the one active legacy run, requests Save and Stop, waits for its completed checkpoint upload, and requests grouped fetching. It does not force-cancel, discard checkpoints, or fall back to a fresh fetch. If stopping takes longer than 20 minutes or a checkpoint is missing, it stops with an explanatory message.

With a `resume_run_id`, the dispatcher reads the saved summary and excludes completed stores with exported files. Only remaining websites are grouped. Each child downloads a copy of the parent checkpoint and selects its own queue. It copies the selected stores' response caches to their new ordinal folders and preserves the saved custom template, source cooldown profiles and store progress. Parent artifacts and completed work remain unchanged. Checkpoint source selection for custom store lists requires the exact original name/URL list supplied through `stores`.

Child artifacts retain their existing names (`chotuapp-excel-files`, `chotuapp-live-logs`, `chotuapp-checkpoint`) and are isolated by Actions run ID. Existing live-download helpers can monitor each group's run ID and follow that group's continuation. The original completed exports remain in their parent run and existing Drive folder; this update does not upload or replace Drive workbooks.

The saved group map is available as `chotuapp-fetch-groups` on the dispatcher workflow. Use the Actions run list to obtain each group's active run ID. A source 429 still pauses the affected website; splitting different websites does not override site limits.

For one combined read-only terminal report, run `catalog-tools/watch_all_runners_windows.py`. It discovers all active/queued fetch jobs every 60 seconds, follows new continuation run IDs automatically, caches immutable artifact IDs to avoid repeat downloads, and reports each store separately. Old snapshots and unchanged counters are warnings to inspect logs, not declarations of a hang. Ctrl+C stops the local monitor only. The latest report is saved as `Desktop/Cloud_All_Runners_Report.txt`; this monitor does not stop jobs or replace Excel downloads.

Scheduled manual retries are recorded as pending before they obtain a worker slot, with the previous status/detail preserved separately. Group continuation can requeue a terminal result once when its recorded extractor revision differs from the installed revision. A same-version block stays terminal, cooldowns remain intact, and the per-revision marker prevents repeating an early startup failure forever. These queue changes do not claim the underlying source error has been repaired.

Latest override: newly dispatched groups contain at most three websites per runner. Existing five-store checkpoints remain readable and can be partitioned into groups of three and two after saving and stopping their source run.
