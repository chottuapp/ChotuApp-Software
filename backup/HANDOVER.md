# Owner workflow and operational handover

Owner: Anas Khan; prefers concise Roman Urdu updates, direct cloud checks and action rather than repeated Windows commands. Time zone Asia/Karachi.
Repository: chottuapp/ChotuApp-Software. Captured source revision: ea50c341812759e44b937496b79ec70f488d1e85. Always inspect latest main before further changes.

## Required delivery pipeline

Complete fetching/export → Rule 804 → independent 804 Audit of every product's category and description → only PASS may upload to Google Drive. No guessed prices, inventory, product facts or fabricated completion claims. Keep original work and source provenance.
Destination: ChotuApp 19-10-2026 11-36AM
https://drive.google.com/drive/folders/17GbkIwSowcPdqyK3rFxhfc9nqkI-yUan
Replace only the same store's file after backup and checksum verification, with rollback on failure; keep other stores' files. Earlier daily-folder instructions are superseded.

IMPORTANT OWNER UPDATE: Unknown shop codes are permitted BLANK. Do not hold a file solely because no confirmed code exists. Confirmed codes match existing workbooks by code; unknown blank-code delivery matches only the approved exact store filename. Nonblank unconfirmed codes still require review. Full content audit remains required. Registry: cloud/confirmed-shop-codes.json. Preserve locked Products columns: shop_code, product_id, Category. Do not invent codes.

Rule 804 full instructions: Rule-804-SKILL.md and docs/rule-laam-and-804-audit.md. Preserve distinct supported facts, useful details, all unaffected fields, prices, stock, variants, images, IDs, formulas, styles and website display order. Infer specific product-purpose categories from actual name/description evidence with attribution; do not claim inferred labels are observed website taxonomy. Ambiguity remains held. Independent bounded automatic audit is not human review or proof of full source coverage.

## Rule LAAM — applies only to LAAM

Fetch visible, active, in-stock clothing: stitched, unstitched and ready-made. Exclude hidden/OOS products and non-clothing such as jewellery and bags. Only source-available variants; preserve explicit prices and exact product state. See docs/RULE_LAAM.md, laam_source_support.py, tests/test_laam_owner_filter.py. Do not apply the clothing-only restriction to Khaadi or other stores without owner instruction.

## Campaign, checkpoints and status

Current campaign: fresh804-20261021-a26dcd86; 29 stores; fresh from zero, maximum three stores per cloud runner. Subsequent restarts resume saved work, not from zero. Khaadi operates on the phone/local Pakistan connection because GitHub-hosted public pages redirect to a foreign storefront. Never substitute foreign prices. Do not claim phone activity without fresh telemetry or user log.

Report branches: runner-status-reports, drive-sync-reports, android-build-reports, local-run-status. Read latest.json and timestamps. Other evidence/report branches are enumerated in repository-refs.json. audit804-held-inputs stores durable raw workbooks and rollback inputs; preserve them. Actions artifacts can expire; not all checkpoint bytes live in Git.

Last observed report 22 October 2026 05:45 PKT: 26/29 fetch complete, 11 fresh audited Drive uploads, 15 held outputs, no active cloud fetch runs. LAAM and Gul Ahmed last runs failed. Stylo exported but audit error 'Unconfirmed shop code; held for review'; investigate unconfirmed populated code rather than disabling content audit. Khaadi phone heartbeat absent; user previously supplied successful HTTP200 product-page fetch logs. These are snapshot facts, not current status.

11 fresh verified uploads: Miss Rose, Tawakkal Fabrics, The Hanger Pakistan, Vince Care, Islamabad Tea, Seran, Shop Modest, Adam Cheese, Farda Foods, Nisa Naturals, Denim Leftover.
Other held files have real category/description findings; do not auto-pass all files to clear the queue. Rawayat care-text false perfume bug was fixed, but missing descriptions and unresolved classifications remain.

LAAM timeout repair at ea50c34: requests Timeout/ConnectionError become TemporaryProductError (deferred product/cooldown path), while TLS failures remain blocked. It resumed checkpoint39586312392 as run39620052330; latest report subsequently says failure, so inspect latest diagnostic logs before another restart. No guarantee unknown parser changes can repair themselves safely.

## Android

Studio package com.chotuapp.studio, current delivered stable release1.4/versionCode5. Stable signed APK included; consult studio-release.json for hash/signature. Original com.chotuapp.mobile signing identity differed; never promise in-place upgrade across packages/signatures. Persist local session, explicit lock, Android Keystore token, foreground worker, offline retry and saved-response resume are implemented; Android force-stop/background limits still apply.
GitHub connection is separate from local app login. Token never belongs in chat or logs. Missing Android heartbeat means connection cannot be confirmed. Private signing material is not in this public backup; keep an encrypted private owner copy separately.

## Important boundaries

Do not modify production databases/AWS resources or unrelated online-shipping code without understanding and authorization. Preserve unrelated main-branch changes and owner files. Delete only identified disposable caches; do not remove workbooks, fixtures, checkpoints, backups or credentials. No chat assistant keeps monitoring between turns: workflows/foreground services perform background work, and report freshness must be verified each time.

For tests use a Python environment with project dependencies; common invocation:
PYTHONPATH=tests:cloud:. python -m unittest test_audit804 test_audit804_delivery test_audit804_semantics test_laam_source test_laam_owner_filter test_auto_continue -q
