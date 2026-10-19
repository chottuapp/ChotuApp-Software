# Default website listing order — 18 October 2026

The current user preference supersedes cheapest-first and bestseller merchandising. Export products using the observed category navigation order and the default product-grid order within those categories. Verified source labels replace category/subcategory presentation for matched products. Product IDs, source variant IDs, prices, stock, availability, SKU, images and option relationships remain unchanged.

The fetcher inspects public header navigation and recognized collection product grids. It follows actual next-page links without forcing another sort. A sort explicitly selected by the website's default controls is retained when paging. Recommendations, footer links, sitemap order, alphabetical catalog APIs, discounts and inferred sales are not ranking evidence. Unsupported layouts, source restrictions and finite capture limits are explicitly unverified; an observed prefix does not establish full-store coverage.

## Optional Products fields

| Field | Meaning |
|---|---|
| `website_category_order` | Observed navigation category position |
| `website_subcategory_order` | Observed navigation section/subcategory position |
| `website_product_order` | First observed position in that default collection listing |
| `website_order_source_url` | Inspected category page supporting the position |
| `website_order_checked_at` | Evidence check time; saved-run responses can be cached |
| `website_order_status` | `observed_default_listing` or `unverified` |

Use the three order numbers lexicographically only when status, same-store source URL, timestamp and positive positions are present. Keep unknown records in their original relative order after observed records. Do not use price or bestseller priority as an undocumented fallback. Keep provenance and internal analysis notes in administration/audits rather than customer-facing claims.

The final workbook preserves this order even after price/quality checks. Links and cell formatting follow their products. Existing popularity observations may remain as historical/source-attributed analysis but do not override default listing order. Rule 804 uses these website positions by default; historical cheapest-first ordering requires a new explicit user instruction.

A completed workbook from an earlier run is not retroactively website-verified. It requires a new source-order capture/rebuild. New engine processes use the updated policy; code is not injected into already-running store processes.


Strict website category policy

Product categories are independent of default display order. A SALE/New Arrivals placement can keep its display rank without becoming the product category. Categories come only from an unambiguous same-store product breadcrumb or a product’s verified membership in a substantive collection actually linked in the store navigation. Breadcrumbs take precedence, followed by the deeper observed menu hierarchy. Source spelling and case are preserved. The full hierarchy is retained in website_category_path; category and subcategory contain the first and last source levels.

Four provenance columns accompany categories: website_category_path, website_category_source_url, website_category_checked_at, website_category_status. Unverified categories are blank and generate WEBSITE_CATEGORY_UNVERIFIED review warnings. Existing unproven categories do not become trusted merely by retaining a previous workbook. Robots restrictions, request bounds and missing/ambiguous source data remain explicit limitations. Category keyword guesses, title-case rewriting and Rule804 editorial taxonomy are disabled in strict exports.

## Description-based subcategory fallback (19 October 2026)

The owner now authorizes inference for missing subcategories. Verified website paths/labels take precedence. For a website with a single category level, its exact label also serves as the subcategory. If no website label is supported, the local classifier reads the supplied product name and description, distinguishes complete outfits from components, and treats genuine bundles separately. An unclear or conflicting product type stays blank. This does not infer sales, change prices/variants, reorder products, or turn an inferred label into verified website taxonomy.

Products exports append `subcategory_source`, `subcategory_evidence`, and `subcategory_checked_at`. Source values distinguish `website`, `inferred_description`, `inferred_product_name`, `existing`, and `unverified`. Evidence is a website path or a short quote from supplied text. Existing nonblank subcategories are retained during batch repair; the fetcher still validates website category provenance first. Category audit CSVs include this evidence. Inference requires no extra requests or paid model API. It is a bounded rule-based classifier and cannot identify every ambiguous catalogue item.

A running GitHub runner keeps its checked-out version. This update applies to subsequent runs/continuations using the updated main branch; it does not hot-reload an existing runner or overwrite previously downloaded files.

## Locked public category header (19 October 2026)

The updated default Products template starts with `shop_code`, `product_id`, `Category`. `Category` contains the final former-subcategory label, not the broad internal website parent category. There are no separate `category` or `subcategory` data columns in this default template. The engine retains internal parent/path evidence and maps the leaf/fallback label to the public `Category` header. Audit fields `subcategory_source`, `subcategory_evidence`, and `subcategory_checked_at` retain their names for compatibility. Confirmed shop codes are populated by exact store hostname; unknown codes stay blank and supplied codes take precedence.

Old/custom template snapshots are retained for compatibility and are not silently rewritten. New runs using the updated default template use the locked header; continuing an older snapshot requires selecting/migrating the desired template separately. This is a saved format contract, not Excel password protection. It does not deploy changes to a separate application importer.
