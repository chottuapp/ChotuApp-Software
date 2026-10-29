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

## Verified upload before old-file replacement

Owner requires the new workbook to exist and pass checksum verification on Drive before touching the old store filename. DriveIdentity.replace stages under _incoming/<sha256>/, checks it, promotes to the existing filename, checks the final destination and then removes the staging copy. Rollback preserves/restores the original on failure. Do not revert this to delete-first delivery.

Owner supplied codes for all eight additions on28 October: Bachaa Party SE10035, Prime Ticks SE10036, Hilm Chapals SE10037, Xcessories Hub SE10038, Design by DAS SE10039, Golden Rose SE10040, Zyren SE10041, Pyari Walls SE10042. Earlier blank-code instructions are superseded. cloud/confirmed-shop-codes.json is the authoritative canonical-name mapping; Golden Rose Pakistan and ZYREN are owner aliases, not additional stores.

29 October owner update: Bachaa Party is OFF like LAAM/Khaadi until explicitly enabled. Registry entry enabled=false blocks fresh dispatch, runtime start and auto-continuation. Preserve checkpoints.43 registered,40 enabled,3 off. Xcessories Hub fetch completed3044 retained products but independent audit still needs source-backed category corrections; query current reports before counting it delivered.

29 October Xcessories recovery: xcessories_purpose_support.py provides source-named object rules (accessories take priority over compatibility targets). audit804_semantics.py independently checks purpose, with explicit watch/tablet accessory guards. Five identity/description-hash-bound source covers were reviewed for model-only object types. Preserve prices, discounts, source variants and all non-requested cells. Recheck drive-sync-reports for actual delivery status; local pass is not upload confirmation. Bachaa Party/LAAM/Khaadi remain off.

29 October fresh expansion supersedes earlier solo/preserved-Stylo plan:58 total stores,55 enabled,3 paused (Bachaa Party/LAAM/Khaadi). Fresh generation refresh20261029-b80f4ca4 restarts enabled old and new stores from zero, two websites per runner,28 runners total. See current audit804/drive-sync release files.15 new store codes remain blank by owner authorization. Habitt MUST stay kitchen-only; collection_scope_support.py and scoped website-order capture prohibit whole-store fallback. User repeats this restriction explicitly. Old completed files remain until audited/verified replacement. Do not count previous generation uploads as this fresh generation.

Breakout uses a headless primary site; public products.json404 there. breakout_source_support.py verifies that primary HTML advertises checkout.breakout.com.pk and bktt.myshopify.com before using the official checkout storefront with the unchanged canonical Shopify extraction/price/stock checks. No public storefront token is copied or committed. Delivery permits checkout.breakout.com.pk only for Breakout.

29 October held-file repair: all 17 previously held inputs independently passed strict all-row audits locally (31,122 Products rows). Files: Bata, Saeed Ghani, Rawayat, Beechtree, ChenOne, Hush Puppies, Habitt, Mala, Sana Safinaz, Beyond East, Alkaram Studio, Generation, Breakout, Saya, Rios, Edenrobe, Limelight. Evidence is identity/description/image-bound in audit804-image-reviews.json and exact public merchant facts in audit804-reviewed-source.json; reviewed_source_types.py excludes generic types. Source photos establish the sold object, never prices/stock or garment contents inferred from model styling. Audit independently verifies photo identity, source cover and original description hash; explicit quantity/stitching conflicts and commercial checks remain gates. Saya review-widget cleanup has a separate cleaned-description binding while original evidence stays intact. Beyond East WTSE361039 canonical title confirms one-piece shirt; only the copied two-piece-suit phrase is corrected, preserving other specifications and options. Missing optional data is not invented.

Deployment dependency: cloud-drive-sync installs ftfy==6.3.1 and smoke-checks repair imports before Drive work. A previous missing dependency produced technical holds, not data changes; rerun the latest revision to clear those. Local pass does NOT mean Drive uploaded; read drive-sync-reports latest.json and compare fresh generation plus verified timestamp. Final upload promotion remains new-copy-first with checksum verification and rollback. Khaadi/LAAM/Bachaa Party remain OFF; preserve active fetch checkpoints.

29 October 2026 owner LOCK — ChenOne (chenone.com): NO furniture. Fetch all other product types under existing price/stock/804 rules. Bedding, bedspreads, sheets, pillow/cushion covers, table linen and other non-furniture goods remain included. Enforce during discovery and before audit/Drive; remove matching furniture across linked variant/image/options sheets. No account-wide memory claim.

30 October PKT: Repair remaining Junaid/Zellbury/Gul Ahmed/Xcessories holds using explicit named sold objects and exact current merchant breadcrumbs; source-cover review binds three Benks cases. Sparse title-only descriptions gain only a factual object sentence, preserving all existing measurements/options and inventing no composition/warranty. Fix independent HTML stripping so numeric inequalities (<0.1%, >90dB) do not swallow intervening microphone specifications after Unicode normalization. Numeric-preservation and semantic checks remain strict. CI now runs numeric-comparison safeguards before Drive changes.

30 October recovery performance: GitHub held-input restoration now downloads only the exact store manifest/chunks over authenticated bounded HTTPS and retains full per-part and final SHA checks, identity/path validation. Non-GitHub local remotes retain the tested Git roundtrip. Xcessories real 3.9MB source restored in 1.0 seconds; formerly each restoration fetched the full expanding held-input branch. Exact current Gul Ahmed Russet Quilt Cover JS confirms all variants unavailable; timestamped receipt excludes it before audit/upload under owner no-out-of-stock rule. No stock inferred from absent description fields.

30 October owner supplied 12 new confirmed shop codes: Sana Safinaz SE10043, Edenrobe SE10044, Beechtree SE10045, Liberty Books SE10046, ChenOne SE10047, Generation SE10048, Saya SE10049, Hush Puppies SE10050, Habitt SE10051 (kitchen-only), Beyond East SE10052, Rios SE10053, Mala SE10054. Existing canonical store names are retained; SAYA/RIOS/MALA and Habitt — Kitchen are owner display aliases, not new stores. Authoritative mapping is cloud/confirmed-shop-codes.json. All prior mappings preserved, no duplicate codes. Code-change detection reaudits and replaces existing blank-code same-name/source-host Drive files; verified upload/promotion precedes removal. ChenOne furniture remains excluded.
