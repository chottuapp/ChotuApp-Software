# ChotuApp Online Shipping Software

Run on GitHub's computers, with no laptop installation or browser console scripts.

**[Open software / Run workflow](https://github.com/chottuapp/ChotuApp-Software/actions/workflows/chotuapp-shipping-online.yml)**

1. Sign into the repository, select **Run workflow**, and leave branch **main**.
2. Enter up to five public HTTPS store or individual product links. Set Pakistan city names and a page budget.
3. Press the green **Run workflow** button, open the new run and expand the fetch step for live logs.
4. After the run finishes, open **Artifacts → ChotuApp-Shipping-Results**. The download includes Excel, CSV, timestamped logs, source evidence, errors and summary. GitHub retains these for 30 days; save important results.

Excel contains Products, Evidence, Errors and Run Summary sheets. Column A/B and the header remain frozen while scrolling. Every run is separate; existing catalog files, Drive files and shop codes are not changed.

## What this version verifies

Product names and links are collected from public HTML links and Product JSON-LD. Only explicit product-specific PKR shipping data with Pakistan destinations can populate city rates automatically. Loose policy prose is retained as evidence for review, never turned into a guessed fixed charge. Conditional or conflicting rates need review. Delivery data may require checkout details unavailable from public pages.

**Not Verified does not mean free shipping.** No rates, inventory counts or full-site coverage are promised. This version does not submit addresses, build carts, place orders or bypass website access controls. Robots policy is checked first; 403, robots denial and timeouts are recorded. CZone may remain blocked even on GitHub runners; that requires an authorized source/export from the store.

Each store is limited to 1–500 pages, each response to 3 MB, and total fetch time to about 45 minutes. At least one second separates requests, with longer robots delays respected. The first version discovers HTML-linked product/listing/policy pages; it does not execute JavaScript, enumerate every sitemap or automatically calculate checkout shipping. Products discovered but not visited are clearly labelled. GitHub Actions usage counts against the account's private-repository runner allowance.

Local developer validation: `python -m pip install -r online-shipping/requirements.txt`, then `python -m unittest discover -s online-shipping -p 'test_*.py' -v`.

## Live viewer

The separate viewer in `online-shipping/viewer/` lets you submit links, inspect runner status and saved product results, copy all logs and download Excel/CSV from the same screen. The browser polls GitHub every 15 seconds; the runner publishes progress approximately every 30 seconds on an isolated `shipping-results-RUNID-ATTEMPT` branch. Results and logs remain private in this repository. No Drive or existing catalog files are modified.

The viewer requires a fine-grained GitHub token for this repository with **Contents: read** and **Actions: read/write**. Enter it only in the viewer's password field, never chat. It stays in memory, not localStorage, cookies, URLs or repository files. Disconnect or closing the tab clears it. Authorized source requests still run on GitHub, not on your laptop. Live counters/logs appear during fetching; the results table and Excel are available after final export. The table displays up to 300 matching rows; the Excel includes all captured rows.

### First publication

This checkout has Git push access but GitHub management API access is denied. Pages must be enabled once from an owner-authenticated CLI or repository Settings → Pages → Source: GitHub Actions. A private repository requires a GitHub plan that permits Pages. **Do not make the data repository public to resolve that restriction.** The Pages viewer contains no product data or credentials; visitors still need an authorized connection to access private results.

After the code is pushed, the repository owner can run these in authenticated CMD:

```cmd
gh api --method POST repos/chottuapp/ChotuApp-Software/pages -f build_type=workflow
gh workflow run shipping-viewer-pages.yml --repo chottuapp/ChotuApp-Software
```

If Pages already exists or GitHub returns an account/permissions error, inspect that response before changing existing site settings. The **Publish Shipping Viewer** run reports the actual deployed URL; no live URL is claimed until that deployment succeeds.

`PyariWalls_FINAL.xlsx` has not been uploaded in this session. The present exporter uses its documented standard audit workbook; it does not claim to reproduce an unseen Desktop template.
