# Fetching ranking implementation

The cloud engine now supports the five optional ranking fields and adds them to resumed/custom templates without replacing existing columns. Only unfinished stores run the new code; completed saved exports are not rewritten automatically.

## Implemented

- Verified Shopify bestseller-grid results include the actual collection page URL, check timestamp and store_bestseller basis in the workbook and BEST SELLERS audit CSV.
- Bestseller verification considers all available exported products, not only discounted products. It is bounded to a verified subset of up to 20 products per store. This is not a claim that five popular products have been verified in every category.
- Category grouping takes precedence over product ranking. Ranked products move within their category; equal/unranked positions use payable price, genuine discount, then stable input order.
- For Elite Cosmetics, Miss Rose, Rivaj UK and Vince Care, recognized beauty/personal-care categories have manual merchandising priority 1; other categories have priority 100. This is a manual category policy, not a sales statistic. Other stores retain their existing category grouping unless explicit category priorities are supplied.
- Missing or unverified popularity is left unassigned. External trends are not inferred or labelled as store sales.
- Final sorting moves full cell records so hyperlinks, formulas, styles and product values stay attached to the correct product.

## Validation and limits

Fixture tests cover verified and unverified grids, evidence provenance, beauty-before-automotive placement, regular-price bestsellers, decimal pricing, blank ranking, hyperlink preservation and generated headless runtime support. Live website extraction for this revision has not yet been run.

This update does not implement cross-website trend research, comprehensive category-specific bestseller collection, or a complete replacement taxonomy for every store. It does not change website importer/storefront code. Existing category classification remains in use. Evidence may be checked from durable responses during a saved-run continuation; the check timestamp does not assert that the page was freshly fetched at that time.

New runs use the latest code. An already active cloud worker must finish or be saved/stopped and resumed before it can use this revision. No active run was stopped or dispatched by this change.

## Per-product analysis notes

The engine now adds analysis_note to every exported product and writes a complete ANALYSIS NOTES audit CSV. Existing product-page responses are inspected for exact recognized labels inside product-information badges; navigation/recommendation text and discount-only labels are excluded. Existing collection membership responses record named Best Sellers, Top Collections, Trending, Most Popular and Featured signals with their actual page/API URLs and check times. Signals are attributed only to products observed in that collection response. No extra per-product requests are added.

Merchant labels/collection membership remain clearly separate from verified best-selling sort positions. They do not by themselves assign product priority or verified-sales metadata. The note states unknown evidence for unverified products and retains manual notes. Final sorting preserves notes with product IDs. Existing completed files are unchanged; new runs and unfinished stores resumed on this revision use the new column.
