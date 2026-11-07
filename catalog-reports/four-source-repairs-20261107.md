# Four requested source repairs — 7 November 2026

Alfateh Garments, Rung Rez and Mansab now have successful software fetch runs. Toynix remains an external access exception: its robots page returns HTTP 403 with a Cloudflare challenge. No challenge bypass or repeated blocked requests were attempted; permitted website-side access or an official feed is needed.

| Source | Exported products | Variant combinations | Successful run |
| --- | ---: | ---: | --- |
| Alfateh Garments | 123 | 339 | [42367456043](https://github.com/chottuapp/ChotuApp-Software/actions/runs/42367456043) |
| Rung Rez | 5 | 13 | [42367458881](https://github.com/chottuapp/ChotuApp-Software/actions/runs/42367458881) |
| Mansab | 61 | 128 | [42367062161](https://github.com/chottuapp/ChotuApp-Software/actions/runs/42367062161) |

These are completed fetch exports with review flags, not final Rule804/checkout approval or verified Drive delivery. Shop codes remain pending owner. The previous twelve completed sources were not restarted. The Paper Worm school-only lock remains applied.

Alfateh: Product Code is a parent identifier, not necessarily a live variant SKU. Uniform-price offers bind to the exact published product and its actual size/colour variants without guessing a selected variant. Non-uniform ambiguous prices and real price/stock conflicts still fail. Dimensions that are explicitly null for every variant are omitted; mixed/missing dimensions stay incomplete. Captured failed socks and multi-variant suit records now pass without changing price, SKU, quantity or option facts. The original checkpoint had expired before recovery; only this failed store was restarted, and its current checkpoint then reused. Checkpoint retention is now three days to permit next-day recovery.

Rung Rez: The Octane/Nuxt public page state explicitly publishes PKR prices and native variant identifiers, stock and options. Only the identity-matched product record is decoded; unrelated Vue Set/plugin state is not executed or treated as product data. This adapter does not inherit LAAM's owner price filter. Whole-rupee display formatting (8243) is accepted only when it matches the source exact decimal price (8242.50) under ordinary positive half-up rounding; the exact decimal is retained. Foreign currency, unexplained display differences and actual offer/variant price differences remain blocking.

Mansab: Normal anonymous Chrome identified the website's actual public `/api/products?slug=...` response. Exact API size_stock, total stock and PKR JSON-LD offers are cross-checked. Fabric, set contents and measurements are retained. Source native variant IDs/SKUs are blank when not supplied; deterministic internal combination IDs are kept separate. Actual size quantities are exported without distributing a shared total or guessing stock. Missing native IDs no longer create false duplicate-native-ID errors; real duplicate native IDs remain blocking.

Validation: source/HTTP export suite 65 passed, identity suite 9 passed, final targeted source/price/description suite 46 passed. The suites overlap. Real public fixtures cover parent codes, optional dimensions, PKR market, display rounding, exact size stock and genuine conflict rejection. All three repaired software runs completed successfully; counts and source revisions are preserved in the companion JSON receipt.
