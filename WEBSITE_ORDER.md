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
