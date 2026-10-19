# Rule 804 — completed 23-workbook repair, 20 October 2026

All 23 published input workbooks were checked under the current saved Rule 804 and owner overrides. Unknown shop codes remain blank by explicit instruction. The previous audit incorrectly treated all unknown codes and optional ranking values as failures.

27,534 products retained. 174 category values repaired (169 formerly blank plus 5 broad labels); 577 descriptions polished. No category blanks remain. Seven workbooks changed; sixteen are byte-identical to their published inputs.

Evidence: 167 official product JSON captures and 22 matched product-image reviews. Two original product URLs returned 404; their archived catalog image references were reviewed without claiming current availability. New visual labels are marked reviewed_product_image. No unverified medical, authenticity, sales or product-material claims were added.

Validation: every unmodified Products XML element is unchanged, all other XLSX parts are byte-identical, all edited cells reopen correctly, product IDs remain unique, source numbers in descriptions remain unchanged, positive product prices checked, and no standalone promotional gift titles found. Prices, formulas, variants, availability, SKUs, image URLs and existing row order were preserved. Source order/ranking status remains explicitly verified or unverified as before; this repair does not certify live website ordering or freshly refetch every inventory/price.

## Separate workbook download links

- [Adam Cheese.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Adam%20Cheese.xlsx)
- [Bonanza Satrangi.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Bonanza%20Satrangi.xlsx)
- [Computer Zone.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Computer%20Zone.xlsx)
- [Cool and Cool.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Cool%20and%20Cool.xlsx)
- [Denim Leftover.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Denim%20Leftover.xlsx)
- [Elite Cosmetics.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Elite%20Cosmetics.xlsx)
- [Farda Foods.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Farda%20Foods.xlsx)
- [Hemani Herbals.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Hemani%20Herbals.xlsx)
- [Islamabad Tea.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Islamabad%20Tea.xlsx)
- [Miss Rose.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Miss%20Rose.xlsx)
- [Nisa Naturals.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Nisa%20Naturals.xlsx)
- [Rivaj UK.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Rivaj%20UK.xlsx)
- [Saeed Ghani.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Saeed%20Ghani.xlsx)
- [Seran.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Seran.xlsx)
- [Shop Modest.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Shop%20Modest.xlsx)
- [Skin Factor.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Skin%20Factor.xlsx)
- [Tawakkal Fabrics.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Tawakkal%20Fabrics.xlsx)
- [The Hanger Pakistan.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/The%20Hanger%20Pakistan.xlsx)
- [Vince Care.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Vince%20Care.xlsx)
- [Outfitters.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Outfitters.xlsx)
- [Rawayat.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Rawayat.xlsx)
- [Junaid Jamshed.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Junaid%20Jamshed.xlsx)
- [Zellbury.xlsx](https://github.com/chottuapp/ChotuApp-Software/blob/main/catalog-files/rule804-20261020-completed23/Zellbury.xlsx)

## Drive installation

The installer downloads only the seven changed workbooks, checks the expected current Drive MD5 hashes before any replacement, refuses unknown/newer versions or duplicate names, uploads with the same filenames without deletes, then verifies all 23 output hashes. Original input snapshots remain in their existing repository paths and are recorded in manifest.json. A partial upload can be resumed. No reports or ZIP files are uploaded into the Drive folder.
