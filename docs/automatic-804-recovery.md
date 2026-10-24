# Automatic 804 recovery

GitHub Actions runs the delivery check every five minutes. Completed files receive Rule 804, the independent all-row audit, and verified Drive replacement. A hold never authorizes upload or deletion of the previous file.

After each completed delivery audit, the public-facts workflow immediately selects at most 40 held product addresses, rotating across stores. It automatically starts Rule 804 and the independent full audit again after the source batch completes. A fifteen-minute scheduled fallback keeps unresolved work in the queue. Each product has a fifteen-minute source-check cooldown to avoid hammering an unchanged or unavailable source. It checks robots rules and the approved storefront. No phone, PC, ChatGPT session, paid AI service or new access token is required for these cloud checks.

Delivery accepts only fresh, matching product titles, handles and approved HTTPS source hosts. It copies primary descriptions and known product types, never prices, inventory, source instructions or executable code. Public evidence is cached with a size bound. Unchanged facts retain the same retry key. Changed facts or reviewed repair rules automatically recheck saved held inputs even after the original Actions artifact expires.

Reports include the exact held product and reason. Known repairs are reusable; unknown types, ambiguous bundle contents and website/parser changes remain held until an evidence-backed repair is added. This system does not claim to write or approve arbitrary new adapter code automatically. Non-Shopify adapters retain their existing recovery paths.

Schedules are best effort and can be delayed by GitHub. Existing checksum verification, source-cell preservation, shop-code identity checks and replacement backups remain mandatory.
