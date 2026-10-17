# Rule 804 — all 13 supplied workbooks, 17 October 2026

Processed the actual uploaded RAR: 12,888 input products; 12,886 retained products across 13 workbooks. Two standalone gift boxes and exclusively owned dependent records were removed.

## Ordering

Products are grouped by corrected category (A–Z), then sorted by current payable product price, lowest first. A valid positive sale price below regular price takes precedence; otherwise the positive regular product price is used. Equal prices use genuine percentage discount descending, then original order. Individual variant prices remain unchanged. This does not claim a per-unit/weight price comparison.

`Category_Budget_Picks.csv` lists up to five cheapest retained products per category. These are budget picks, not verified top sellers or invented sales rankings. No sales popularity was established from this archive.

## Preservation and verification

All retained IDs, names, prices including decimals, SKUs, stock quantities (including blanks), availability, URLs, image links and variants were compared with the supplied originals. Headers, worksheets, formulas and cell styling were checked. Hyperlink row references were remapped during product sorting. Unchanged XLSX ZIP parts remain byte-identical. Related image/variant/option rows were removed only for the two deleted gift boxes; shared option groups were retained. Category price ordering and ZIP integrity passed for every workbook.

Source-supported descriptions, ingredients, directions, composition, care, sizes and measurements were retained without arbitrary length limits. Supplier review widgets and sales filler were removed. Clearly copied Farda paragraphs about different products were removed; actual title and supplied weight were retained. Missing facts were not invented.

## Source limitations

These are polished copies of supplied exports, not a new website fetch or certification that every source value is correct. See `Review_Notes.csv` and `verification.json` for sparse descriptions, incomplete care text, conflicting supplier details and missing images. Existing blank stock/image fields remain blank. No claims of independently verified top-selling order or repaired upstream inventory are made.

## Files

| Store | Products | Variants | Gallery records | File |
|---|---:|---:|---:|---|
| Adam Cheese | 58 | 58 | 58 | [Adam_Cheese_Rule804.xlsx](Adam_Cheese_Rule804.xlsx) |
| Elite Cosmetics | 1558 | 2020 | 2507 | [Elite_Cosmetics_Rule804.xlsx](Elite_Cosmetics_Rule804.xlsx) |
| Farda Foods | 51 | 53 | 94 | [Farda_Foods_Rule804.xlsx](Farda_Foods_Rule804.xlsx) |
| Islamabad Tea | 29 | 29 | 29 | [Islamabad_Tea_Rule804.xlsx](Islamabad_Tea_Rule804.xlsx) |
| Junaid Jamshed | 4800 | 20567 | 16172 | [Junaid_Jamshed_Rule804.xlsx](Junaid_Jamshed_Rule804.xlsx) |
| Miss Rose | 179 | 1846 | 1682 | [Miss_Rose_Rule804.xlsx](Miss_Rose_Rule804.xlsx) |
| Rawayat | 3531 | 4561 | 4239 | [Rawayat_Rule804.xlsx](Rawayat_Rule804.xlsx) |
| Rivaj UK | 297 | 831 | 1146 | [Rivaj_UK_Rule804.xlsx](Rivaj_UK_Rule804.xlsx) |
| Seran | 265 | 789 | 1388 | [Seran_Rule804.xlsx](Seran_Rule804.xlsx) |
| Shop Modest | 138 | 1095 | 1551 | [Shop_Modest_Rule804.xlsx](Shop_Modest_Rule804.xlsx) |
| Tawakkal Fabrics | 1425 | 3254 | 4461 | [Tawakkal_Fabrics_Rule804.xlsx](Tawakkal_Fabrics_Rule804.xlsx) |
| The Hanger Pakistan | 349 | 1519 | 3050 | [The_Hanger_Pakistan_Rule804.xlsx](The_Hanger_Pakistan_Rule804.xlsx) |
| Vince Care | 206 | 356 | 934 | [Vince_Care_Rule804.xlsx](Vince_Care_Rule804.xlsx) |

## Updated persistent preference

The saved project Rule 804 now uses cheaper-first ordering within each category, replacing discount-first ordering. Five-per-category suggestions must be identified as budget picks unless sales evidence is actually verified. This updates this project’s workbook-cleanup rule; it does not hot-reload a running fetch worker.
