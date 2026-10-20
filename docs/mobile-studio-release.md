# Android Studio delivery and updates

Studio uses `com.chotuapp.studio`, separate from the original `com.chotuapp.mobile` preview. The original preview signing private key was not retained; its existing installation cannot accept an APK signed by the Studio key. Never uninstall the original as part of an automated update.

The user chose a fresh Khaadi start in Studio instead of USB data migration. Leave the original paused to avoid duplicate fetching. GitHub credentials are not transferable between package Keystores; reconnect in Studio. Local profile signup does not create an online email/GitHub account.

CI builds and tests a candidate, published as `ChotuApp-Studio-candidate.apk` with its source commit, checksum and device-test result. This is not the stable delivery APK. Final delivery must be signed using the existing privately backed-up Studio key, verified with apksigner, then published as `ChotuApp-Studio.apk` and `studio-release.json` on android-builds. Compare the published signing certificate fingerprint before every subsequent update. Never generate a replacement key for an existing Studio release. Never commit a private signing key/password or put them on the public delivery branch.

The current private working key is outside this repository in `/workspace/.private-chotuapp-signing/`. An offline user backup is `/workspace/delivery/ChotuApp-Studio-Private-Signing-Backup.zip`. Treat both as credentials. If this environment is replaced, restore the private key from that backup before signing an update.

For future releases increment versionCode and read the installed version dynamically when checking updates (the first release checker compares against version 1). Same package and same certificate permit updates while preserving private app data. Android still requires installation consent. Current updater checks the public Studio release metadata during dashboard refresh and opens the fixed repository APK download URL; it cannot silently install or invent repairs.

Progress numbers are stage task counts, not verified catalog/product completeness. Discovery URLs, rows, and page inspections have different units. Overall completion is unknown unless separately verified. Older Drive records without per-store timestamps show that time was not recorded; new uploads record verified_utc after checksum checks.
