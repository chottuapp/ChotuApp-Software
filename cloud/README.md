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
