# ChotuApp: start here in a new Codex session

Owner-authorized GitHub handover prepared 28 October 2026. This repository is the durable context; a new ChatGPT account does not inherit the old chat or identity. Read this document before acting. Use the latest main branch for continued work; backup branches are historical snapshots.

## Read first

1. AGENTS.md and .agents/skills/rule-804/SKILL.md (full saved owner instructions).
2. docs/OPERATIONS_PREFERENCES.md and .agents/preferences/fetch-status.md. The latter includes an OLD 20 October snapshot; never use its counts as current.
3. docs/automatic-804-recovery.md, docs/rule-laam-and-804-audit.md, docs/RULE_LAAM.md.
4. cloud/fetch-update-release.json (store registry), cloud/confirmed-shop-codes.json, cloud/audit804-release.json and cloud/drive-sync-release.json (current configuration).
5. Query live GitHub Actions, runner-status-reports, cloud-reports and drive-sync-reports before giving status or restarting anything. Old failure runs may have successful continuation children.

## Owner's operating rules

- LAAM and Khaadi stay OFF until explicitly enabled. One enabled store per runner.
- Preserve existing work/checkpoints and verified Drive files. Do not restart all stores because of one product finding. New fresh campaigns require owner instruction.
- Exact source PKR prices and sale prices; no guessed discounts, availability or quantity. Exclude fully out-of-stock products. Retain sold-out variants with available=no; no fabricated combinations.
- Preserve observed website default category/product order. Unknown order stays explicitly unverified.
- Pipeline: complete fetch -> Rule 804 -> independent full 804 Audit -> checksum-verified Drive replacement. Failed audits enter bounded source-backed repair, then Rule804 and full audit again. Never suppress findings, invent facts, or delete legitimate products to force a pass.
- Retain complete useful source details in readable customer-facing descriptions. Product identity and categories require evidence.
- Exact source-linked variant images only. General product cover goes in separately labelled fallback metadata; never pretend it is a verified colour-specific image.
- Astore: bags, wallets and mini pouches only, women and men. No unrelated separately sold accessories.
- Hello Maali: CAS01 owner-confirmed code; preserve Size/Planter/Pot Colour combinations; exclude only specified optional gift-box add-ons (see saved rule).
- Do not ask owner for routine CMD/screenshots when GitHub evidence is available. Fix known issues and resume autonomously; report actual access/source blockers honestly. No claim of every-second or continuously online chat monitoring.

## Delivery destination

ChotuApp 19-10-2026 11-36AM
https://drive.google.com/drive/folders/17GbkIwSowcPdqyK3rFxhfc9nqkI-yUan

Replace the matching store only after independent pass and verification; preserve old version until success. Use confirmed shop identity; do not match unrelated stores by a shared code alone.

## Latest known work, NOT live state

Campaign fresh804-20261026-5d42fe35; refresh generation refresh20261027-f31e6f08.
32 stores were restarted fresh, while Stylo run 40477303521 was preserved and completed.
At this snapshot: 31/32 fresh files verified plus Stylo =32 current replacements. Only fresh Sapphire pending. Outfitters 3871 and Zellbury 5841 products passed full audits and verified delivery. Stylo 9357, Bata 1844, Computer Zone 831, Rivaj UK 322 also passed and delivered.
Sapphire run40653526896 was active from checkpoint40549963309. Check it NOW rather than assuming active. Recent fixes handle removed PDP redirects to own empty collection only with exact host/path/canonical and category-page evidence. Never invent a price for an unavailable PDP.
Current fixes are committed on main. Regression suite for latest correction:36 tests passed. Additional previous metadata batch:59 tests passed.

## Working and recovery entry points

- cloud/fresh804_dispatch.py: explicit fresh dispatch and continuation chain preservation.
- cloud/audit804_delivery.py: durable held-input recovery, independent audit and Drive replacement.
- cloud/hold804_repairs.py, cloud/audit804_semantics.py: source-backed classification/description repair and independent checks.
- cloud/image_provenance_repair.py: bounded same-product Computer Zone metadata migration; never alter stock/prices.
- .github/workflows/cloud-fetch.yml: resumable fetching; cloud-drive-sync.yml: delivery.
- catalog-tools/live_status.py: status inspection. Inspect usage before executing.
- Tests: PYTHONPATH=tests:cloud:. python -m unittest <relevant modules>. Install repository dependencies using current setup docs; do not assume old workspace paths exist.

Do not cancel a Drive-writing workflow or dispatch duplicate active stores. Before checkpoint resume, verify artifact availability and preserve current refresh runner_group lineage. Check Actions artifact expiry; an old run ID is not a guaranteed recoverable checkpoint.

## Backup boundaries and credentials

Snapshot backup/2026-10-28 contains source hashes, branch index and credential-free status. Historical code/package backup branch backup-complete-2026-10-22 remains preserved. The new backup branch captures this handover and current code; main retains git history.
Runtime report/evidence/build branches are separate from main. Date-labelled archive refs preserve their current commits; future reports continue on their normal branches. Existing GitHub repository secrets remain in GitHub; a new account/session must be authorized to this repository. They cannot be exported/read back as plaintext. Android signing keys and external Drive credentials require their existing secure storage; this repository snapshot is NOT proof of a separate recoverable secret backup. Never commit tokens, passwords, signing keys, private shop backups or unrelated personal files.
GitHub Actions artifacts expire independently of git branches. Uncommitted workspace files and a full original chat are not automatically recoverable. This handover preserves operational context, not account memory. No PC backup is requested.

## Owner additions later on 28 October

Registry is now43 stores (41 enabled; LAAM/Khaadi off). Eight previously absent stores were added: Bachaa Party, Prime Ticks, Hilm Chapals, Xcessories Hub, Design by DAS, Golden Rose, Zyren and Pyari Walls. Shop codes remain owner-authorized blank. These use the same refresh generation, solo lanes33–40 (in that listed order), same audit/delivery folder. Do not redispatch merely because the original32-store refresh count changed. Xcessories Hub and Design by DAS use the allowlisted public WooCommerce Store API adapter; exact variation IDs/prices/stock are checked. Unsupported types/wildcard variants remain explicit exceptions, never a fabricated pass. Remaining six use Shopify source. Read current reports before giving counts.
