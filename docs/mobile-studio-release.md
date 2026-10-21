# Android Studio delivery and updates

Studio uses `com.chotuapp.studio`, separate from the original `com.chotuapp.mobile` preview. The original preview signing private key was not retained; its existing installation cannot accept an APK signed by the Studio key. Never uninstall the original as part of an automated update.

The user chose a fresh Khaadi start in Studio instead of USB data migration. Leave the original paused to avoid duplicate fetching. GitHub credentials are not transferable between package Keystores; reconnect in Studio. Local profile signup does not create an online email/GitHub account.

CI builds and tests a candidate, published as `ChotuApp-Studio-candidate.apk` with its source commit, checksum and device-test result. This is not the stable delivery APK. Final delivery must be signed using the existing privately backed-up Studio key, verified with apksigner, then published as `ChotuApp-Studio.apk` and `studio-release.json` on android-builds. Compare the published signing certificate fingerprint before every subsequent update. Never generate a replacement key for an existing Studio release. Never commit a private signing key/password or put them on the public delivery branch.

The current private working key is outside this repository in `/workspace/.private-chotuapp-signing/`. An offline user backup is `/workspace/delivery/ChotuApp-Studio-Private-Signing-Backup.zip`. Treat both as credentials. If this environment is replaced, restore the private key from that backup before signing an update.

For future releases increment versionCode and read the installed version dynamically when checking updates (the first release checker compares against version 1). Same package and same certificate permit updates while preserving private app data. Android still requires installation consent. Current updater checks the public Studio release metadata during dashboard refresh and opens the fixed repository APK download URL; it cannot silently install or invent repairs.

Progress numbers are stage task counts, not verified catalog/product completeness. Discovery URLs, rows, and page inspections have different units. Overall completion is unknown unless separately verified. Older Drive records without per-store timestamps show that time was not recorded; new uploads record verified_utc after checksum checks.

## Studio 1.3

A successful local login is remembered in app-private preferences across process restarts and same-key updates. Lock app explicitly clears that session; no plaintext password is saved. Existing profiles log in once after this upgrade.

Public requests wait and retry connection failures, timeouts, 429 and temporary server failures, checking Pause during every retry delay. TLS, access-denied and adapter errors remain visible rather than being retried as successful data. Completed workbook upload retries transport outages without refetching the saved export. The foreground service continues when the activity closes and requests system recreation after process eviction. Force stop, phone shutdown and Android data-sync time limits can still require reopening/resuming; unrestricted battery use is recommended.

Drive displays the current Pakistan date and count of distinct latest verified store uploads on that date. Each store has one latest entry, chosen using upload-verification timestamps; previous versions are not duplicated in the list. The list does not delete Drive files. Audit holds preserve the previous verified workbook.

## Studio 1.4

GitHub connection now requires a successful first redacted phone heartbeat write, not only repository read access. The token remains in Android Keystore; server-side write denials are shown in the connection dialog. Idle app screens automatically sync status on open and about every 30 seconds; the existing foreground worker syncs while fetching with the UI closed. Manual and worker report writes are serialized, branch conflicts retry using the newest file SHA, and unexpected native sync faults are visible. This is not a remote-wake facility: Android force-stop and a phone without a working connection still require opening the app. Reopening after an update resumes a previously requested worker; an explicit Pause is retained.
