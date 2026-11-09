# Loading toolbar recovery and cached-read speed

Run 42590962648 reached scope 29 after retaining 1,167 distinct links. A browser listing timeout was correctly classified as unresolved, but its exception handler then parsed the raw unrendered toolbar. That toolbar had no supported numeric total. The secondary ValueError masked the original browser timeout and failed the store before later scopes could run.

Preserve the original rendering exception and the exact unresolved toolbar text. A normal listing with an unknown toolbar is also a typed unresolved-scope result, retaining actual visible links and continuing remaining scopes. No numeric total is guessed, no unresolved scope snapshot is recorded as complete, and independent complete-catalog approval remains held.

Read already-checksummed saved responses before applying network pacing. Cached reads still check pause/stop and validate response identity, scope, status and challenge markers. They need neither a request nor a 1.5-second delay. Real network requests retain the same pacing, bounded retry and source cooldown safeguards.

Regression checks reproduce the nested Loading toolbar/browser timeout, preserve its original cause, retain visible products with unknown counts, continue other scopes, and prove cached reads make zero network calls and zero pacing waits. Live traversal beyond the failing scope is checked separately from fixture tests.
