# Grocery timeout recovery

Run 42586468420 failed on a requests ReadTimeout during the fresh second page of the Dawn recheck. Unlike the earlier public browser rendering timeout, this exception escaped the source-paused handler and ended automatic continuation. Original checkpoint and source response caches were saved.

The source adapter now retries only transient timeout/connection exceptions three times with bounded waits. Exhaustion becomes an explicit source pause; certificate errors, actual access denials, source challenges and HTTP rate limits retain their existing safeguards. Completed traversal/reconciliation snapshots are stored in the checksummed response cache, including source-total discrepancies, and reused on the same saved generation. Resumes no longer repeat every fresh discrepancy check before reaching unfinished scopes.

A typed browser rendering timeout records an unresolved scope, retains any actual source-visible cards and permits other supplied pages and discovered product details to proceed. Failed rendering is never saved as a completed traversal snapshot. Coverage receipts and every exported row retain review-required status; independent audit still blocks full-catalog approval. Actual rate-limit responses stop rather than hammering subsequent pages. Existing raw responses, price/stock/identity checks, owner categories, pending blank shop code and electronic exclusion remain intact.

Regression tests cover timeout recovery, three-attempt exhaustion, certificate failures, persisted discrepancy snapshots across cache reopen, continuing past unresolved browser scopes, retention of visible cards, and stopping on actual source rate limits. Live completion and exported product counts require separate runtime evidence.
