# Shared delivery and sold-object repair

The Drive identity loader previously rejected an entire folder on any repeated XLSX filename. It now downloads every listed XLSX by its Drive ID into distinct local paths when duplicates exist, indexes all confirmed shop codes, and permits unrelated unambiguous replacements. Copies with duplicate filenames are retained and their replacements remain held. Missing IDs and duplicate copies without a single confirmed code remain fail-closed. No deduplication, renaming or arbitrary newest-copy selection is performed. ID-to-local copy support was checked against the runner's rclone v1.60.1 implementation.

The classifier now recognizes explicit paper journals, stationery sets, pen holders and written multi-piece garment counts before incidental cosmetics or computer nouns. The independent audit separately checks the sold object: abaya versus blush colour, paper notebook versus laptop, pen holder versus its contents, Mary Jane flats versus jeans mentioned in styling, and shalwar/kameez pairs versus individual trousers. Commercial, identity, source order, owner-scope and incomplete-product gates remain enabled.

Validation: 141 relevant tests passed, including 9 new duplicate-identity/sold-object regressions. The existing semantic test `test_jewellery_care_is_not_sold_perfume` fails at unchanged HEAD because its input is rejected as an incomplete description; this was reproduced with both original modules loaded and is not waived or weakened.

Original immutable held workbooks were restored with manifest SHA256 checks, owner exclusions applied, then reprocessed through Rule804 and independent strict commercial audit:

| Store | Retained products | Incomplete excluded | Owner-scope excluded | Audit |
| --- | ---: | ---: | ---: | --- |
| VNS Collection | 536 | 235 | 0 | pass |
| Afrozeh | 155 | 20 | 0 | pass |
| Essence | 40 | 34 | 0 | pass |
| The Paper Worm | 170 | 106 | 18 | pass |

These are local reprocessing results, not Drive upload receipts. Existing verified Drive files must remain until staged and final checksum verification succeeds. Actual duplicate files and unresolved source failures are not claimed resolved by these tests. No fresh fetch batch or environment publication is part of this repair.
