# Fetch update — 18 October 2026

## Verified fixes

- Excel image links use the appended row index, avoiding a full worksheet scan for every image/variant. Values and hyperlink targets remain unchanged.
- Reused variant identities across products/options receive deterministic scoped export IDs. Source IDs, prices, availability, SKU and images remain intact. Exact repeated rows collapse once with an audit finding. Contradictory records fail explicitly instead of silently choosing a price.
- Product row preparation, variant worksheet writing and price audits publish separate live stages. Stage ETA is not an overall completion promise.
- Price audit reports separate unavailable verification (`REVIEW`) from proven differences (`MISMATCH`). Outfitters' nine previous audit findings were HTTP 404 fetch failures, not confirmed price mismatches.
- Successful HTML response caches compress without changing response bytes. Existing raw cache databases remain readable. Corrupt compressed entries are rejected. Failed/rate-limited pages are not cached.
- Automatic continuation includes successful HTML cache entries in its progress fingerprint. Existing finite continuation limit, cooldowns and no-progress protection remain enabled.

## LAAM public source adapter

LAAM has moved to a Nuxt storefront; `/products.json` is not its catalog. The adapter follows declared public sitemaps and reads the exact product page's public state. It requires PKR evidence, observed variant IDs/options, explicit availability, actual image URLs and known publication status. Public quantities are retained; unknown quantities remain blank. It does not infer virtual stock, invent variants or guess bestseller claims.

Four captured public product fixtures verify normalization and the existing workbook export integration. This is fixture/integration validation; a complete live marketplace crawl is still required before claiming complete extraction. The marketplace can contain many thousands of products and requires checkpoint continuation. Source access, robots restrictions, coverage/size limits and price-review findings remain visible.

## Source limitations

Khaadi's Pakistan homepage redirects the cloud runner to its US storefront. Do not export US prices as PKR. Sapphire exposes Salesforce product pages and size controls; its public robots rules disallow the required variant endpoint. Full variant extraction needs an approved public feed/source permission. Explicit source guards report these limitations instead of repeatedly trying an unrelated Shopify endpoint. These sources must not be labelled complete by suppressing errors or inventing prices/stock.

## Resume

The latest verified checkpoint is Actions run `39124854389`, containing 24 saved workbooks. Resume this checkpoint after updating; completed store outputs remain unchanged. An export marked REVIEW still needs its audit checked. Automatic continuation does not make permanent source failures disappear.

## LAAM option-order repair

The actual failing product `0085` lists Stitching Type before Kids Size in its options array, while its explicit source positions specify Kids Size first. The adapter now sorts by validated positions before mapping observed variant titles. It retains all four variants (including three out of stock), source IDs, prices, stock counts, SKU and images. Missing/duplicate/invalid positions are rejected rather than guessed. Parser/schema failures now report `ADAPTER ERROR`, while verified source access/locale failures retain `SOURCE BLOCKED`.

This update does not hot-replace code inside the active store process or cancel the current Zellbury work. It applies when a new saved-run resume prepares the updated engine. Existing successful response caches are retained.

## Faster LAAM resume

Successfully parsed products now have a durable, checksummed cache inside their own saved-run folder. Cache identity includes the exact adapter file revision, so parser updates revalidate from successful saved HTML instead of reusing stale interpretations. Corrupt records are rejected. Script-only parsing avoids constructing the whole storefront DOM for each page. No source pacing, stock, prices or option validation is relaxed. The next validated release resumes checkpoint `39136925448` and retains its 25 saved stores.
