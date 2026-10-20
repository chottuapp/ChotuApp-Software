# ChotuApp Android preview

Native Android app, minimum Android 8 (API 26), arm64 phones and x86_64 emulators. No Termux or PC is required. The embedded Python exporter uses the same reviewed Khaadi sources and locked template; only unused desktop Tk import statements are removed during packaging. Source hashes are checked before packaging. Public requests use normal TLS checks and do not change the Pakistan source/currency/variant validation.

## Screens
- Overview: phone Start/Resume and safe Pause, actual worker status, source events, reported cloud runner count, fresh batch verified upload count, fixed Drive destination and source timestamps.
- Activity: retained local logs and source-provided cloud snapshots. Unavailable or stale reports do not prove current activity.
- Settings: encrypted GitHub connection, Android background settings, Drive shortcut.

## Connect
Khaadi can fetch without credentials. To queue its completed workbook for Rule 804 and Drive, create a fine-grained personal access token for `chottuapp/ChotuApp-Software`, repository Contents: read and write, and paste it into the app's Connect dialog. Never paste it into chat. The account needs repository write access. The token is encrypted using an Android Keystore AES-GCM key, excluded from backups and never included in APKs/reports. Disconnect clears the stored credential.

The app sends the completed workbook and checksum marker to the already configured cloud pipeline. A queued upload is not a verified Drive upload. Verification is matched to that exact raw workbook SHA256. Existing matching-name versions are replaced and unmatched stores remain in `ChotuApp 19-10-2026 11-36AM`.

## Runtime limits
Keep the phone on and online and permit background operation. The ongoing notification exposes Pause; a wake lock supports active work. Force-stop, battery management, reboot or Android data-sync foreground time limits can end the worker. The next Start/Resume reuses saved responses. The app does not secretly restart after a manual pause or bypass Android limits. Unknown parser errors require a tested adapter/app repair; no prices or stock are guessed. This first APK embeds the reviewed source release; it does not download arbitrary executable code. Existing Windows cache is not transferred. Catalog completeness and unresolved editorial/source warnings remain unverified.

App-private files and saved work are lost if Android app data is cleared or the app is uninstalled. This is a debug-signed preview, not a Play Store production release. The build caches the preview signing key to support updates while that cache remains available; a durable production signing key must be configured before relying on long-term in-place upgrades.

## Verification and delivery
`android-apk.yml` builds the APK, boots an Android 35 emulator, launches the native Activity, tests encrypted credentials, and exports a captured Khaadi fixture through embedded Python/SQLite/openpyxl. It publishes the APK only if these checks pass, along with `android-builds:latest.json` (commit, SHA256, build time) and a screenshot. No live phone/Pakistan-source success is implied by an emulator fixture test.

## Version 1.1: remote logs
With GitHub connected, the active worker publishes a redacted tail of the last 60 local events every 30 seconds to `local-run-status:local/khaadi-android.json`. The Android path is separate from the PC heartbeat. The combined status report selects the newest device report and marks old heartbeats stale. This records source progress/errors; it is not continuous observation by a chat session.

Overview shows the log-sync status. Activity provides Send logs now and a manual view refresh which preserves scrolling while reading. Connecting during a fetch takes effect without restarting the fetch; final workbook delivery also uses the current connection. Missing credentials, expired tokens, denied repository access and offline retries are visible instead of being silently ignored. Fetching remains independent of telemetry success. A final stopped/exported/error snapshot is attempted when the worker exits, subject to Android/network availability.

Logs remove the current token, GitHub token patterns, credential-bearing lines and private app-storage paths before publication. No headers, cookies, raw response bodies or credentials are uploaded. The publisher verifies the previous and new APK signing certificate matches before offering the update, so users can install over the existing app and retain its data. Do not uninstall to apply this update.

### Signing incident in the first installed preview
The first successful APK used an ephemeral signing key. The configured Actions cache path did not contain the actual key, and diagnostics confirmed no `chotuapp-preview-signing-v1` cache was saved. Subsequent builds therefore have a different certificate. The release guard correctly refused to replace the existing download with an incompatible update. An in-place 1.0 → 1.1 update must not be promised; the first private key cannot be reconstructed from its public APK certificate.

Keep the installed 1.0 app and its saved work. It can publish a one-minute progress/error heartbeat after GitHub connection and Pause/Resume. The full-tail 1.1 source has passed tests but has not been delivered as an update. Any migration requiring uninstall must first have a concrete verified backup and explicit user authorization. `catalog-tools/backup_android_app_windows.py` prepares a read-only USB backup after an in-app pause, checks two complete tar streams match, hashes all files, and never installs, uninstalls, resets or deletes app data. It does not export Android Keystore credentials. A durable, separately backed-up signing identity is required before any replacement release.
