# Importer-compatible Excel files

Seran_Importer_Compatible.xlsx retains every original sheet and cell from the
uploaded Seran export, with additive importer-compatible columns. All 257
products' 1,355 image links are represented across the main-photo and pipe-separated
gallery columns. Product IDs, prices, availability, descriptions, variants and
source image rows are unchanged. Exact importer aliases are supplied for sale
price, scraped/main image, option group title and option image.

Chotu_Products_Import_Template_Updated.xlsx is a blank reusable template using the
same compatible structure. Original populated input files were not modified.

Import the populated Seran file first and inspect one product's gallery and sale
price. The actual importer code was not supplied or changed; runtime acceptance
and its support for extra sheets must be tested in the application. Variant
Combinations remain present but this file cannot add combination support to an
importer that does not implement it.
