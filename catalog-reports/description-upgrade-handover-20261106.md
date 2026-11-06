# Description software release — 6 November 2026

The owner requested substantially better English product descriptions and permitted restrained emojis/boxes. The shared software now renders source-bound customer copy with relevant Unicode headings and bullets. Examples: [before and after](description-upgrade-20261106.md).

Fresh fetching, desktop installers/bundle and the saved-workbook Rule 804 pipeline use the same renderer. It retains sourced materials, ingredients, measurements, directions, precautions, warranty and exact option values. It removes known sales padding and generic category sentences; it does not invent missing specifications or benefits. Concise explicit facts are valid without artificial word-count padding. This remains deterministic source-based editing, not a separate generative AI writing service or human review.

The independent audit now checks substantive content apart from name/code/options. Genuinely incomplete products and their linked rows are excluded under the owner's existing policy; price, stock, identity and conflicting-fact failures remain blocking. Original inputs remain durable and unchanged. Every excluded identity/reason is archived in a separate receipt; public report summaries are bounded to 100 entries without limiting the actual all-row audit. Over-capacity descriptions are quarantined instead of silently truncated.

Explicitly targeted reprocessing can reuse a previously passed input only if it matches the exact source run and SHA of the current verified Drive receipt. It cannot replace a newer source with an old workbook. Delivery still stages and checksum-verifies the replacement before promotion.

Validation: 129 focused repair/audit/source/installer/description checks passed. Original Bata, Rawayat, Rios and Stylo sources passed the full independent audit after permitted incomplete exclusions; final release reprocessing and remote receipt verification are tracked separately. Desktop ZIP was extracted, installed into an isolated directory and smoke-checked. Existing GUI tests require a display unavailable in this headless environment; no GUI behavior changed.

Final local validation: Bata 538 retained / 1,354 incomplete; Rawayat 3,982 / 638; Rios 2,390 / 42; Stylo 8,196 / 1,283. Every retained product passed strict full audit with zero findings. The eight real HTTP export fixtures also passed. These are local release-validation counts, not a claim of completed Drive delivery. [Targeted delivery runner](https://github.com/chottuapp/ChotuApp-Software/actions/runs/42214329978).
