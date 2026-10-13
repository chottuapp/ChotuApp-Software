Daily Auto Fetch is an optional fixed panel. Existing extraction buttons remain.

Close the application before installing install_daily_auto.py. The installer backs up the main file and support modules. It adds startup hooks and updates Saved Runs support; the extraction engine, speed constants, prices, images, templates and saved data are preserved. Daily automation starts disabled.

Choose a template and tick stores, then enable Daily, optionally enable Open at laptop login, and click Save selected stores. The saved selection is independent of later checkbox changes. Time is local Windows HH:MM. Run on opening if today is pending starts a fresh daily run even before the configured time; disable it to wait for that time. Each subsequent day starts a fresh run; successful responses from an earlier day are never reused for a new daily run.

If today's own automatic run was interrupted, reopening the app resumes its saved responses. Those responses reflect when they were originally fetched. On a later day, automation starts fresh. An unfinished manual run is preserved and blocks an automatic fresh start until the user resolves it. Only one window owns daily automation. Extraction failures require explicit Continue Saved Run; there is no automatic retry loop. Reviewed exports remain reviewed.

Each completed store saves immediately in ANAS_DATA_FETCH. Existing backups/output replacement behavior remains unchanged. Daily output names remain the store names; this update does not create a separate dated output archive.

The Windows per-user Startup folder contains only the owned ChotuApp Daily Auto Fetch.cmd launcher. No administrator rights or passwords are needed. The launcher opens pythonw when available. It starts after Windows login, not before login. Disable Open at laptop login and save to remove only this owned launcher. Disable Daily and save to stop daily fetching.

The laptop must be powered on, logged in, awake and connected to the Internet. The app must stay open for the configured time; there is no hidden service or wake-from-sleep task. Fetching rules and rate-limit backoff remain unchanged. Percentage badges remain calculated unless independently verified source text is available. The importer/app must support the template's new columns.
