# Optional category and product ranking fields

Use `Chotu_Products_Import_Template_ShopCode_Ranking.xlsx` for the complete template with shop codes, stock, discount tags and ranking metadata. It has 34 Products columns, including the internal analysis_note field. All existing product, variant, stock and image field meanings are unchanged.

## Added Products fields

| Header | Type | Meaning |
|---|---|---|
| category_priority | Nullable positive integer | Store-specific category display priority; lower first. The same shop/category must use a consistent value. |
| product_priority | Nullable positive integer | Product display priority within its category; lower first. |
| popularity_basis | Nullable enum | `store_bestseller`, `external_trend`, or `manual_selection`. |
| popularity_source_url | Nullable HTTP(S) URL | Actual evidence page; required for store_bestseller and external_trend. |
| popularity_checked_at | Nullable ISO 8601 timestamp | When the evidence was actually checked; required for evidence-based rankings. |

Blank priorities mean unassigned, not zero. Do not invent sales rankings, evidence links, timestamps, or badges. Manual merchandising is allowed but must be identified as manual_selection, not verified sales. Category priority is merchandising metadata and does not itself assert popularity. Imported evidence still requires provenance and freshness checks before customer-facing claims.

## Ordering contract

1. Within each shop, display categories by assigned category_priority ascending, with unassigned categories last. Ties preserve the existing category order; do not force alphabetical ordering that promotes an unrelated side category over a store’s primary offering.
2. Within a category, display assigned product_priority ascending, with unassigned products last.
3. Within equal/unassigned product priorities, sort by payable product price ascending: use a positive sale price only when below the base price; otherwise use base price.
4. For equal payable prices, use genuine percentage discount descending, then original import order.

External marketplace popularity is an external trend signal; it is not evidence of a particular shop’s sales. Do not label manual selections or external signals as verified store bestsellers. Never let metadata override actual product/variant pricing or availability.

## Implementation requirements

- Import by header name; new fields are optional for backward compatibility.
- Preserve valid existing ranking metadata if an update omits these columns. Define an explicit clear operation rather than erasing metadata due to a missing column.
- Reject invalid enum values, non-positive/non-integer priorities, conflicting category priorities within a shop, invalid URLs, and invalid timestamps with row/column errors.
- Scope category and product ranking to the correct shop and product IDs.
- Store priorities and evidence separately from prices and stock.
- Verify importer persistence and storefront sorting with a beauty-store fixture where a primary beauty category precedes an unrelated automotive category, and with priced and unpriced priority metadata.

## Scope of this delivery

The template columns, input validation, embedded Ranking Guide and this contract are delivered. No ranking values have been invented. Existing completed exports are unchanged. This delivery does not implement automated evidence collection, migrate an active cloud worker’s saved template, or change website application code. Those require separate fetching/importer/storefront implementation and verification.

## Internal product analysis note

`analysis_note` is optional plain text on every Products row. Preserve it for admin review and Rule 804; do not automatically append it to the customer-facing description or show it as a bestseller badge. It records verified storefront-sort evidence, explicit product-page merchant labels, collection membership signals, source URLs, check timestamps and missing-evidence limitations. A top/featured/trending collection label is not verified sales volume. Unranked products receive an explicit unknown-evidence note rather than an invented ranking. Saved-run notes may refer to cached responses; a check timestamp is not a guarantee of a fresh network fetch.
