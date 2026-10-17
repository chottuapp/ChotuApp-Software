# ChotuApp Cloud

Two deployment options use the existing extraction engine without changing the Windows application. The online dashboard is a single-owner service. There is no public running instance until it is deployed to a host.

## Option 1: fetch with the PC switched off, using GitHub Actions

No separate hosting account is needed. Use the GitHub account that owns this repository.

1. Open **Actions → ChotuApp Cloud Fetch → Run workflow** on the `main` branch.
2. Enter stores as `Name | https://store.com; Other Name | https://other.com`. Choose the total time budget, from 1 to 300 minutes.
3. Click **Run workflow**. Once GitHub shows the job as running, your PC can be switched off.
4. When the run finishes, open that run and download **chotuapp-excel-files** under **Artifacts**. Each completed store and its audit files are included even if another store failed.

[Open the workflow](https://github.com/chottuapp/ChotuApp-Software/actions/workflows/cloud-fetch.yml)

This is a bounded background job, not a permanently running website. The fetch budget defaults to 285 minutes, leaving time to upload files within the workflow's 330-minute limit. Standard Linux runners for public repositories are generally offered without a compute charge; GitHub's current account settings, policies, queue availability and artifact storage quotas still apply. This task could not retrieve the official billing/limits pages through its network proxy, so it does not claim verified current free allowances or unlimited storage. See [Actions limits](https://docs.github.com/en/actions/reference/limits) and [billing](https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions) before using large runs. Artifact retention is one day: download files promptly. Public-repository run logs and artifacts are accessible according to GitHub's public repository permissions; use a private repository for private catalogs, with its applicable compute/storage allowance. No private PC settings or runtime credentials are committed by this integration.

**Continue another Actions job:** optionally tick **save_checkpoint**. This creates a checkpoint artifact only if its compressed size is at most 250 MB. On the next run enter the previous run's numeric **resume_run_id**; the store input is ignored, completed stores are skipped and saved responses are reused with current installed code. Download the checkpoint within one day if keeping it. Large response caches can exceed this limit; the job reports that no resumable artifact was saved, and the completed Excel files remain available. An abrupt runner termination can prevent checkpoint upload; GitHub Actions does not supply durable always-on disk. The persistent dashboard below is the appropriate option for long-running or large resumable work.

Cloud datacenter IPs can be blocked by a store even when a PC request works. The existing price, availability, variant, category, image and rate-limit checks still apply; a blocked/incomplete source is not relabeled as successful.

## Option 2: persistent online dashboard

A Docker-capable VM/server with persistent storage and HTTPS is required. A free-tier VM may work when available; no hosting account, allocation, credit-card check, billing plan or public domain has been provisioned by this repository. Free sleeping web hosts do not satisfy continuous background fetching. GitHub Pages hosts static files and cannot run this worker.

The dashboard provides:

- Store selection and custom store URLs.
- New Fresh Run, Pause, Resume, Stop & Save and Continue Saved Run.
- Optional XLSX template upload; the supplied discount-tags template is the default.
- Per-store progress and downloads as each workbook finishes.
- Bounded live logs, free-disk display and password-protected access.
- Two isolated website processes, preserving per-source pacing and stricter throttling rules.
- Persistent checkpoints, outputs, learned source pacing and template snapshots on `/data`.
- Automatic continuation after a server restart, unless the user paused or stopped the run. A fresh run never silently starts on login.

### Start on a VM

Install Docker Engine and its Compose plugin on the host. From the checkout root:

```bash
export CHOTUAPP_WEB_PASSWORD='use-a-unique-long-password-here'
docker compose -f cloud/compose.yml up -d --build
```

Use username **admin** and your configured password. The service binds only to host loopback on port 8080. Put Caddy or another HTTPS reverse proxy in front; `cloud/Caddyfile.example` is a minimal example using an actual hostname pointed to your VM. Do not expose Basic authentication over plain public HTTP. Credentials belong in host environment/secret settings, never in GitHub files or chat.

The Docker build installs Tk import support without starting a desktop window and installs Playwright Chromium for Czone's existing catalog browser fallback. The application runs as a non-root user. A named Docker volume stores data across container replacement. `restart: unless-stopped` restarts the service when Docker starts. Volume loss, VM deletion, provider sleep and host outages still stop work; back up the data volume. Do not remove the volume when updating the service.

```bash
git pull --ff-only
docker compose -f cloud/compose.yml up -d --build
```

Stop or pause and stop the current worker before updating. The regenerated runtime uses current repository code and preserves response caches; Czone's derived parsing cache follows the software revision. Continuation retains the interrupted run's responses; start fresh for fully refreshed prices and availability. The desktop program, its stores and Excel files are independent of the cloud volume. The cloud does not automatically upload results into the Chotu admin importer.

### Local development / CLI

Use Python 3.12 with the root `requirements.txt` dependencies and system Tk support. No additional web framework is required.

```bash
CHOTUAPP_WEB_PASSWORD='a-unique-test-password' CHOTUAPP_CLOUD_DATA=/tmp/chotu-cloud python cloud/server.py
python cloud/cli.py --data .cloud-data --stores 'Farda Foods | https://fardafoods.com' --minutes 285
python cloud/cli.py --data .cloud-data --continue-saved
```

The optional Czone browser fallback additionally needs `playwright==1.55.0` and its Chromium installation. The Docker image installs these. The Actions workflow installs them when Computer Zone is selected or a checkpoint is restored.

Validation: `python -m unittest discover -s tests -p test_cloud.py -v`. Tests use controlled stores and real subprocess workers; live-store reachability and cloud speed are not guaranteed by fixture tests. Container deployment and external account provisioning are separate from these tests.

## Validation in this development session

26 cloud and existing scheduler/process tests passed, including authenticated HTTP downloads, cross-origin control rejection, real subprocess fetching, pause/stop/restart with updated source, checkpoint restore, unchanged desktop source and headless import of the actual extractor. Desktop/mobile browser checks also passed: login, polling, selection and adding stores, with no JavaScript errors or mobile horizontal overflow. JavaScript syntax and workflow/Compose YAML were checked. The full Docker image build was attempted twice but could not reach the Ubuntu package mirrors because container DNS resolution is unavailable in this environment; container build and live external hosting are not verified. GitHub API calls are blocked in this session, so an Actions run must be started from the repository UI.


## Seran catalog denial handling

The cloud runtime includes a Seran-only public-source fallback. A healthy normal catalog is unchanged. If `/products.json` explicitly returns 403, the adapter tries the public `/collections/all/products.json` feed, preserves its product/variant/image data, validates complete pagination and requires exact handle coverage against the public product sitemap. A custom or partial collection, missing sitemap, duplicate product, malformed schema or denied feed is rejected; no incomplete workbook is published. The source becomes **blocked**, while other stores continue. Existing pacing, rate-limit cooldowns, saved responses and price checks are retained. This is not a guarantee that Seran permits GitHub datacenter access; live validation of the alternate feed was unavailable from this development environment's network proxy.

Each finished cloud run now drains its final log messages and writes `run-summary.json` next to its Excel files, plus a GitHub job summary with each store's status and exported product/variant counts. This prevents a missing last console message from obscuring an otherwise saved file. Checkpoints and completed outputs remain available on partial failure. The workflow pins Ubuntu 24.04 to avoid an unexpected runner OS migration. No Windows source, template or Excel data is replaced by this cloud update.

## Automatic diagnostic reports

Each future cloud run collects bounded per-store HTTP status counts, observed network response timing, cache events, status, product/variant counts and source revisions. The collection step runs after handled fetch failures too. It uploads `chotuapp-diagnostics` with `report.json` and a redacted tail of up to 2,000 log lines, retained for one day.

A separate, non-blocking `diagnostic-archive` job archives **only the allowlisted structured JSON**, never raw logs, response bodies, credentials, settings, databases or Excel files, to the `cloud-reports` branch. Files are `latest.json` and `runs/<run-id>-<attempt>.json`. The fetch job keeps read-only repository permissions; only the short archive job gets contents-write permission. A private temporary Git index constructs the report commit without switching branches, replacing the application working tree or force-pushing. Archive failure does not discard completed workbooks; inspect that job if reports are missing. The report branch appears on the first successful archive job. These reports are public when the repository is public.

Reports are available for subsequent diagnosis without manually pasting full logs. The chat assistant does not receive push notifications, does not keep monitoring when the conversation is idle and does not update application code automatically from telemetry. Ask it to inspect the reports; native Git access can read `cloud-reports` even when the session's GitHub API access is unavailable. Abrupt job cancellation, host termination or an earlier checkout/setup failure can prevent collection/upload; this is not a guaranteed external monitoring service.

Validation: 46 cloud/source/scheduler/diagnostic tests passed. Tests cover metrics/redaction, absent run state, publication allowlists and two real commits/pushes into a local bare report branch while keeping main and its files unchanged. Actual GitHub archive permissions and delivery must be verified on the next cloud run. Up to 30 stores are accepted; 15 links can be queued, with two website processes active at once. The five-hour fetch limit and checkpoint size limit are unchanged.

## Live text logs and automatic PC downloads

New workflow runs launch **one continuous** extractor under a background supervisor. Sixty short composite-action checks wait up to five minutes each. They copy only queue entries marked done whose recorded output size/mtime still match, and upload changed completed workbooks to `chotuapp-excel-files`. They replace `chotuapp-live-logs` with a current diagnostics snapshot and a redacted full text log. The extractor is not restarted between checks. Snapshot uploads add a small transfer delay and can fail independently; they do not accelerate or bypass source requests. Final diagnostics, files and optional checkpoints still upload at the end. An unexpected supervisor exit is detected. The normal fetch budget, source gating and checkpoint rules remain unchanged.

`cloud_sync_windows.py` uses the user's installed, authenticated GitHub CLI; it does not read or print the authentication token. It polls every 60 seconds, downloads new artifact IDs only, and saves completed files to `Desktop/ANAS_DATA_FETCH/Cloud_<run-id>/`. Text logs and status go in that folder's `logs/`. Local workbooks with different contents are backed up under `previous-cloud-files/` before replacement. Checkpoint databases are not downloaded automatically. The helper stops local sync on Ctrl+C without cancelling the cloud job. On a completed run it also saves `logs/github-full-log.txt` using GitHub's full run log.

```cmd
py cloud_sync_windows.py --run RUN_ID
```

The PC must be on with this sync command running to download files. When the PC is off, cloud extraction and snapshots continue, subject to the host's run limits. Relaunch the helper after turning the PC on. Artifacts still expire after one day. A workflow already running before this update cannot gain live snapshot steps retroactively: for older runs the helper saves current status while waiting, then downloads available final logs/files. Do not cancel a productive old run merely to obtain live uploads; its completed results should be preserved first.

Validation: 56 focused tests passed, including an actual detached supervisor surviving its launcher exit and snapshot checks; recorded-size/mtime checks; complete text retention beyond the rotating tail; incremental local sync; existing-file backup; artifact ordering; existing source, checkpoint and price-related behavior. Workflow and composite YAML and Python syntax were checked. GitHub's live artifact publication and Windows-native execution require confirmation on the next live run. No claim is made that this development session can monitor a running user's PC.

Product stock and variant image export
--------------------------------------
New default templates include `stock_quantity (kitni quantity bechni hai)` in Products.
Shopify product quantity is the sum of explicit nonnegative integer inventory counts
only when every variant reports a count and none explicitly disables inventory tracking.
Missing, partial, untracked or negative counts remain blank; availability is never converted
to an invented quantity. Czone exports availableQuantity only with inventoryTracking=1.
Variant quantity remains blank. No fallback of 100 is used.
Exact variant images are resolved from featured_image, image_id or gallery variant_ids.
Options receive an image only if the linked variants have one unambiguous image URL;
combination rows retain their own mappings. Image URL cells are clickable hyperlinks.
These are spreadsheet/export changes; customer-facing display requires importer/app support.
Existing custom templates need the product stock column added to receive the new field.

Safe stop and resume (new runs)
------------------------------
Use `gh workflow run cloud-stop.yml --repo chottuapp/ChotuApp-Software -f run_id=RUN_ID`
instead of Cancel workflow. The active snapshot monitor checks successful stop requests
roughly every 30 seconds (API/network delays can extend this). The supervisor requests
normal extraction shutdown, then the CLI saves its checkpoint, including successful
responses and completed store outputs. A safe stop requests a checkpoint even if the
original save_checkpoint input was false. Wait until the fetch run has ended and the
`chotuapp-checkpoint` artifact exists before starting again. The stop request workflow
succeeding alone does not mean the checkpoint is uploaded.

Resume with `gh workflow run cloud-fetch.yml --repo chottuapp/ChotuApp-Software --ref main
-f resume_run_id=RUN_ID -f minutes=300 -f save_checkpoint=true`.
Completed stores are left alone; unfinished stores reuse saved responses with current
code. Old template snapshots receive the stock column without losing custom columns.
A paused run can finish with exit code 2 because work remains; check artifacts rather
than assuming that exit code means saved work was lost. Checkpoints still have a
250 MB compressed limit and 1-day retention. A hard cancellation, upload failure,
expired artifact or oversized checkpoint cannot guarantee continuation. This is a
resume improvement, not a promise of increased website request throughput.

Dated PC Excel archive
----------------------
The Windows sync helper also keeps Excel files under
`Desktop/ANAS_DATA_FETCH/Save daily data with dates/YYYY-MM-DD/`, using the PC's
local download date. A new export from another run uses `Seran (1).xlsx`,
`Seran (2).xlsx`, etc. Files are never overwritten in this archive. Repeated live
snapshots of the same run/file/content are archived once, even after restarting
sync. Changed file content within a run creates another numbered copy. The next
date starts again at `Seran.xlsx`. Cloud-run folders and logs remain available.
The PC must be on with the updated sync helper running to create local files.

Observed category rate-limit update
-----------------------------------
Rawayat, Rivaj UK, Junaid Jamshed and Tawakkal now start at one worker with
at least 1-second shared request spacing after observed HTTP 429 at 0.25 seconds.
Learned slower intervals and server cooldowns still take precedence. Cloud scheduling
allows five automatic retries after the initial attempt and waits up to 15 minutes
for each server cooldown, bounded by the CLI's overall time budget. Other stores
continue during those waits. Source-paused worker events are labelled WEBSITE COOLDOWN
rather than FAILED; schema, identity, price and completeness failures still fail closed.
This reduces repeated rate-limit failures; it does not guarantee website acceptance
or certify review workbooks as final.

Price fidelity, stage progress and per-store audits
--------------------------------------------------
New exports validate and preserve source PKR decimal amounts instead of truncating
fractional values. Previously completed/restored workbooks are not silently re-priced.
They retain their earlier audit warnings and need a separate fresh verification to
recover any decimals already removed by an older exporter.

The live store-status.txt now includes the last sampled prefetch task counts, sample
age and last successful HTTP response time in UTC. Stage ETA uses consecutive task
samples and is labelled as an estimate for that stage only; it excludes later workbook
building/audits and is suppressed when the sample is over three minutes old or the
store is not running. This does not increase website request throughput.

Newly completed workers copy available per-store audit CSVs to ANAS_DATA_FETCH/audits;
live Excel artifacts include those reports, and the normal checkpoint retains them
with the output folder. Restored stores whose old checkpoint did not include reports
cannot have those historical audits reconstructed from status counters alone.

Large checkpoint handling
-------------------------
The former 250 MB compressed cutoff caused a real stopped run to lose its downloadable
resume checkpoint. New saves keep legacy checkpoint.zip for small archives and split
larger archives into checksummed 250 MB parts plus a manifest, uploaded together as
chotuapp-checkpoint. Resume supports both formats and verifies part order, sizes and
SHA-256 checksums before extraction. Limits are 2 GB compressed and 8 GB expanded,
with free-disk checks; GitHub artifact quotas and 1-day retention still apply. Splitting
does not reduce total storage or guarantee an upload. Already deleted/expired checkpoints
from earlier workflow revisions cannot be recovered by this code update.

One automatic continuation
--------------------------
The user authorized one additional 300-minute continuation for Actions run 38970499270.
A separate workflow_run handler on the default branch observes its completion. It
requires a trusted main-branch manual dispatch, unfinished stores, an explicitly saved
and available checkpoint, and evidence that the extraction time budget expired. For
that already-running revision it reads the console-tail budget message; new runs record
an explicit stop_reason in run-summary.json. A manual save-and-stop, cancellation,
source failure alone, missing/oversized/expired checkpoint, or complete catalog does
not trigger a continuation. The handler dispatches current main with the parent's
run ID and auto_continue_once=false. The child will not automatically chain again.
Duplicate completed-event processing checks for an existing named continuation.
Future manually launched runs may explicitly opt in with auto_continue_once=true;
the default is false. Cloud and artifact quotas still apply. This is a bounded resume
feature, not a way to avoid GitHub time or storage limits. Live dispatch requires
GitHub's workflow_run event and token permissions and was not exercised locally.

One-window live PC sync
-----------------------
cloud_live_windows.py supervises the local sync helper. It checks current main every
15 minutes and replaces a changed helper only after its download compiles successfully;
it restarts only the local child, reusing persisted sync/archive state. Unchanged source
does not restart the child. Cloud fetching is not paused or cancelled by these updates.
This supervises local downloading, not arbitrary hot replacement of active extraction
code. Latest cloud extraction code is applied at the next checkpoint continuation.

The updated sync helper prints the downloaded store-status.txt in CMD when it changes,
and follows a named automatic continuation after an authorized budget-expired parent
finishes with a saved checkpoint. It waits up to 10 minutes for that child, preserving
the daily-folder layout. Live GitHub uploads remain five-minute snapshots; local
polling cannot make an old cloud workflow publish more frequently. Browser/app UI,
prices, variant mapping and website pacing checks remain unchanged.

Cached HTML transport now returns its already-checksummed response directly instead
of reading and hashing the same body twice through nested cache wrappers. Tests keep
the pause control and checksum-corruption fallback, shared pacing, HTTP endpoints and
exported workbook values intact. This reduces cache work, not the website's required
cooldown; overall real-store speed improvement has not been benchmarked.

Progress-display and local network retry fixes
----------------------------------------------
Completed stores no longer show old partial prefetch samples as active task progress.
The PC helper also cleans that presentation for already-running older cloud snapshots,
without modifying the downloaded original report. Local GitHub metadata calls time out
after 120 seconds and artifact downloads after 10 minutes, then retry through normal
sync handling. A timeout does not cancel cloud fetching. The live launcher picks up
helper changes on its regular update check without a manual CMD restart.

Audit-driven parsing and stage fix
----------------------------------
The 17 October diagnostic bundle confirmed Rivaj's API prices agree, while 202
static theme-price checks remain pending, and Rawayat has one product lacking cover
and gallery images, 554 short source descriptions and 11 generic option titles.
These are not automatically repaired or hidden. A confirmed parser gap now accepts
whitespace after Rs/Rs. as well as PKR within existing theme-price selectors. This
fix is locally tested; it does not prove all 202 Rivaj theme pages are supported.
The telemetry collector now resets old prefetch counts/ETA on known stage transitions
and displays Building Excel rows or Saving Excel workbook when appropriate, rather
than suggesting the last task sample is still running. Active older cloud code is
unchanged until the next continuation.
