# Stylo — Rule 804 and shop code SE10010

Source: completed online fetch run 39020395288, input catalog-inputs/Stylo_39020395288.xlsx.

- 9,414 products retained; no paid gift sets removed.
- 45,164 variant combinations and 41,113 gallery records preserved.
- 48 product-type categories and 224 category/subcategory combinations replace misleading sale/collection labels.
- Complete source measurements, size options, composition, care and all numerical description facts retained; descriptions edited without arbitrary length limits. Sparse or incomplete sources are documented in Review_Notes.csv.
- Category display priority is manual merchandising: footwear 1, bags 2, apparel 3, lingerie/hosiery 4, accessories/gifts 5, home 6, toys 7, beauty/fragrance 8. This is not a popularity claim. Within each category, products are ordered by valid payable price ascending, genuine discount descending for equal prices, then original order.
- Product popularity fields remain blank because this supplied workbook contains no verifiable bestseller evidence. Budget picks are not verified top sellers.
- Product IDs, retained original columns, decimal prices, stock including blanks, availability, SKUs, image URLs, cell styles/formulas and hyperlinks checked. Every non-Products workbook ZIP part is byte-identical to the source.
- Added shop_code = SE10010 for every product and five optional ranking fields.

## Download

[Stylo_Rule804_ShopCode.xlsx](Stylo_Rule804_ShopCode.xlsx)

The Windows download helper verifies the SHA256 in verification.json, then uses the existing daily archive helper to save the workbook under Desktop/ANAS_DATA_FETCH/Save daily data with dates/YYYY-MM-DD. Existing files are not overwritten; numbered filenames and repeat-download deduplication follow the saved archive rule. Original Stylo.xlsx is preserved.
