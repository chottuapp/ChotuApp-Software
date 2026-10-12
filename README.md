# ChotuApp R5 catalog quality update

The original RAR remains unchanged. Updated desktop source is `main.py`.

## Catalog rules

- Exclude public products with no available, positively priced variant. Preserve
  ALL source variants of included products, setting unavailable variants to `no`
  in both Options and Variant Combinations. Do not invent combinations.
- Exclude known Shipping Protection/Back In Stock Apps services/placeholders.
- Normalize beauty categories using explicit product wording before generic
  collections. Apparel wording takes precedence over color words such as blush.
  Unknown categories remain reviewable rather than invented.
- Build descriptions only from source text. Remove repeated headings, scripts,
  duplicate sentences and shopping prompts. Keep concise facts, without adding
  unverified claims. Missing source detail remains short and is flagged by audit.
- Preserve API gallery images, including source variant images. Verify the cover
  against recognized product-page hero markup or og:image, matched to that
  product's gallery. Unmatched/unsupported/rate-limited pages retain the API
  fallback and create an IMAGE AUDIT REVIEW record; fallback is not called verified.
- Put the first 20 included products from a confirmed storefront best-selling
  collection grid at the top of Products. Ignore recommendations/navigation;
  check up to five pages when sold-out products are excluded. If ranking cannot
  be confirmed, retain ordinary ordering and require REVIEW.
- Preserve base and sale price fields, integer truncation policy and API audits.
  The separate mobile importer must honor sale prices and exact combinations.

Image verification makes additional paced requests. On rate limiting, stop
further image-page requests and save reviewable output with verification gaps.
Existing FINAL files and previous exports retain backup protection.

## Windows update

Close ChotuApp. Extract `ChotuApp_Fixed_R5.zip` into a separate folder and open
CMD in its inner `ChotuApp_Fixed` folder:

```bat
py install_update.py
py "%USERPROFILE%\Desktop\ChotuApp_Software\main.py"
```

For a custom installation, use `py install_update.py --target "D:\your\folder"`.
The installer verifies a timestamped backup, then replaces only main.py. If
runtime dependencies are missing, run `py -m pip install -r requirements.txt`.
Choose the original template, select stores, and click FETCH SELECTED. Template
choice is persisted. Touchpad tap-hold/drag on store rows and page backgrounds
scrolls; a normal click selects a store. Native inputs/buttons retain behavior.

## Development and verification

Use Python 3.12 with Tk and requirements.txt. A display is required for GUI tests:

```sh
python -m unittest discover -s tests -v
```

22 automated tests passed. A separate live Miss Rose eyebrow export verified
sale 499, four shades including unavailable 01, all four API gallery images,
website hero first, cleaned description and Eyebrow category. This representative
export isolates catalog enumeration and ranking; the live ranking helper was
verified separately. Whole-store and other-theme validation remain outstanding.

Tests cover source-only description cleanup, canonical categories, product-hero
matching, rejection of unrelated images, verified best-selling grids/pagination,
stock filtering, preservation of unavailable variants, sale prices, decimal
policy, existing FINAL preservation, GUI scrolling/drag, selection, Pause/Resume,
worker failure and REVIEW status. Controlled fixtures establish code behavior;
they do not prove arbitrary website theme support or importer compatibility.
