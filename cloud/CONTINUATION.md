# Checkpoint continuation

A manual cloud-fetch dispatch defaults to four additional checkpoint runs. Set
`auto_continue_limit` to an integer from 0 through 48. Each continuation has a
300-minute fetching budget; GitHub job, storage and account limits still apply.
This is a bounded chain, not an always-on hosting service.

The legacy `auto_continue_once=true` input still authorizes one additional run
when no positive chain limit is supplied. To disable chaining, use limit 0 and
leave that legacy flag false. Manual stop/cancel, missing checkpoints, completed
work, permanent failures without recoverable work, or two runs without durable
progress prevent another dispatch. A long source Retry-After is respected;
continuations do not bypass website limits. Automatic children skip terminal
failed/blocked sources; a manual resume retries those with the current code.

Progress fingerprints count saved successful API/page responses and completed
exports. Local downloads follow each permitted child and retain daily versioned
files. A PC shutdown only stops local downloads.

For the current incomplete batch, manually resume checkpoint 39068755244 rather
than restarting all stores. Existing exports remain intact. HTTP 404 on LAAM,
Khaadi and Sapphire requires inspection of actual public source responses before
claiming adapter support. Run cloud-source-check.yml to capture those responses
and the Outfitters/Zellbury source metadata. The diagnostic performs at most
three ordinary requests per host, respects robots and stops at access denial or
rate limits. It publishes only a limited public summary to source-reports; raw
public fixtures expire as an Actions artifact after one day. It does not fix or
claim successful extraction from unsupported platforms.

## Large restored batches

Restore preflights the declared uncompressed size against both a 24 GiB maximum
and actual free disk space, retaining 1 GiB for working files. Unsafe paths and
duplicate ZIP members are rejected before extraction. This lifts the old 8 GiB
ceiling without disabling expansion or disk checks. The workflow restores once
before optional browser setup; valid completed Czone exports do not trigger a
new Chromium installation. Pending or missing Czone exports still do. Restored
progress is verified on the next cloud run; a larger-than-24-GiB archive or
insufficient runner storage still requires a different recovery strategy.
