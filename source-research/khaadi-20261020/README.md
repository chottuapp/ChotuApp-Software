# Khaadi Pakistan public source findings — 20 October 2026

User-supplied curl captures verified HTTP 200 with final host pk.khaadi.com. These are local Pakistan observations, not proof of cloud-runner locale behavior. Fresh cloud locale checks now bypass saved-response cache.

The supplied robots.txt allows the sampled canonical product paths and sitemap_index.xml, but disallows /on/demandware.store/. The sitemap index points to sitemap_0.xml; complete catalog coverage was not collected or verified.

The black and purple Cambric Kurta public JSON-LD offers state PKR 6000.00 and PKR 5500.00 respectively. Their pages contain matching outfit components with separate product IDs and prices; those must not be combined with the main kurta's variants. Main product size labels are XS/S/L and XS/S/M/XL respectively. Product-level InStock statements, empty `instock` attributes and unselected availability widgets do not establish exact per-size stock or prices. Radio control values reference the disallowed variant endpoint; no requests were sent to that endpoint.

`khaadi_public_evidence_support.py` extracts these observations and explicitly returns import_ready=false and variant_data_verified=false. It is an evidence parser, not a completed catalog importer. Synthetic regression tests cover product/component separation, unknown size facts, foreign currency and identity mismatches; both actual user captures were also parsed locally. Captured full HTML, transient session values and cookies are not included in this repository.

A complete variant adapter remains blocked on a verified permitted source with size-level prices and availability, such as a merchant export/feed or an authorized API integration. Exact product order/category coverage and cloud Pakistan routing also need independent verification before a complete export can be claimed.
