# Khaadi on Android

This runs the approved Khaadi public-page adapter inside Termux's Ubuntu environment on the phone's own internet connection. It does not route GitHub requests through a proxy or disable TLS checks. Pakistan product identity, currency, selected size, price and stock checks remain mandatory. A working phone source is not yet live-verified. Discovery coverage remains unverified.

Install Termux from https://f-droid.org/packages/com.termux/ (the terminal app). Allow background operation / unrestricted battery use in Android settings. Have at least 3 GB free initially; saved responses can grow beyond this. Keep the phone on, connected and Termux active. Turning off the PC does not stop the phone; Android may still terminate background apps.

In Termux, download and run `catalog-tools/install_khaadi_android.sh` from this repository. This installs Ubuntu, Python/Tk, curl, GitHub CLI and the existing exporter dependencies. At GitHub's device login prompt, sign in as an account with write access to this repository. Never paste a password, token or device code into chat.

Re-running the same installer resumes files under `~/ChotuAppMobile`; it does not erase them. It takes a per-device lock, retries temporary network errors, and checks the approved, checksum-pinned worker release. An unknown parser error waits for a tested published repair. This does not automatically author arbitrary code fixes. Stop with Ctrl+C. Do not run the Windows and phone Khaadi workers at the same time if you want one unambiguous heartbeat.

On export, the phone retains the raw workbook and sends only that workbook plus a checksum marker to `catalog-inputs/khaadi-mobile/`. The cloud uploader explicitly opts this Khaadi workbook into the shared Rule 804 preservation/classification pass, requires Pakistan source URLs, then copies and checks the processed workbook in **ChotuApp 19-10-2026 11-36AM**. Same-name files are replaced; other stores remain. No raw workbook is sent directly to Drive. `original_uploads.Khaadi` records verification separately from the fresh 26-store count. The automatic Rule 804 pass preserves unresolved warnings and is not a full editorial/source-coverage audit.

The phone's credential-free heartbeat uses `local-run-status/local/khaadi.json` with `execution: Android Ubuntu local`. A stale heartbeat is not proof of an active worker. Existing PC caches are retained on the PC and are not silently transferred to the phone.
