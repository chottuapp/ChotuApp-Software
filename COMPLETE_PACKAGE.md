Complete ChotuApp source bundle — 2026-10-19

This ZIP contains the current extraction engine, source-safe adaptive pacing, durable saved runs, variant prices/images, stock handling and website-default listing order. Existing source-backed descriptions, product/variant identities, prices and image links are retained. Whole unavailable products and explicit free gifts are excluded; unavailable variants of an available product are retained.

Website taxonomy has priority. Missing subcategories can now be inferred locally from the supplied product name and description. The separate fields `subcategory_source`, `subcategory_evidence`, and `subcategory_checked_at` distinguish observed website labels from inferred product types; unclear/conflicting items stay blank. Inference uses no extra requests or paid model API, changes no sales ranking, and does not make inferred labels into verified website categories.

The displayed default website navigation/listing order supersedes the older discounted-first and forced best-selling policies. Unknown relative order stays stable. Stock quantities remain blank when unavailable rather than receiving a fabricated default. Discount percentages are calculated from prices; exact source badge text remains blank unless independently verified.

Compatibility: Products includes legacy fields and importer aliases/gallery_urls. Variant Combinations includes exact dimension values, source variant ID, base/sale prices, availability, image, and discount columns. This desktop software generates XLSX; it does not implement the ChotuApp backend importer or storefront variant selection behavior.

To install over an existing Windows app: close it, extract ZIP to a separate folder, open CMD there, run `py install_complete_update.py`. It backs up and replaces program files, preserving existing settings, user templates, exports, checkpoints and store lists. Restart `py "%USERPROFILE%\Desktop\ChotuApp_Software\main.py"`. Select the Discount_Tags template via Browse file for new exports; Continue uses its saved template snapshot. Dependencies are not reinstalled automatically; for a clean installation run `py -m pip install -r requirements.txt` if needed.

For a separate development copy: install requirements, then `py main.py`. Source uses the existing Desktop data paths, so use an isolated account or explicit local path overrides when testing. Regression tests are in the GitHub repository tests/ directory, not in this source ZIP; they use temporary paths and fixture data. Linux GUI tests need a virtual display; Windows touchpad and Windows login startup require hardware verification.

Daily automation and the owned Windows login launcher have been removed. Fetching is manual: select stores and use FETCH SELECTED or New Fresh Run. Continue Saved Run resumes the prior saved queue. Pause does not cancel a run; close the window to leave its saved progress, then reopen to choose a new fresh run. No unattended refresh timer is active.

Manual-run cooldown recovery processes other stores before retrying a rate-limited source. It retries at most twice after cooldowns of at most 120 seconds; longer delays or continued blocking stay pending with a Website cooldown status. No scheduled fetching or login startup is enabled. Shop Modest and Elite Cosmetics use a one-worker conservative profile.

Adaptive Speed recovers historical slow pacing after 80 consecutive fresh HTTP 200 responses, reducing the interval 10% per successful window toward the source-safe floor. Caches do not create false speed-recovery signals; rate-limit protection and bounded retries remain. A plain-text fast path preserves normalization output while avoiding unnecessary HTML trees.
