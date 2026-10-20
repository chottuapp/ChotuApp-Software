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
