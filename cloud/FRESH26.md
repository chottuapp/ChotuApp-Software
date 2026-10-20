# Fresh 26-store pipeline

The Windows `start_fresh26_rule804_drive_windows.py` helper creates one uniquely
named `cloud-fresh26.yml` dispatch, remembers its ID, and reconnects on rerun.
The dispatcher selects the registered 29 stores minus LAAM, Khaadi and Sapphire;
no saved source/checkpoint is supplied. Nine groups of at most three stores each
are dispatched. Existing excluded solo lanes and their automatic descendants
are allowed to continue; any other active fetch prevents an overlapping batch.

Fresh runners have `fresh26-` group IDs. On each changed completed-file snapshot,
`rule804_pipeline.py` applies the current deterministic product-purpose category
rules, confirmed shop codes and conservative supported description corrections.
Unchanged formulas, workbook parts, prices, variants, stock, images and source
ordering are checked. Invalid schema/prices/orphan references, attempted formula
overwrite and possible Excel description truncation hold the workbook. Category
ambiguity remains blank with a manifest warning. The automation preserves source
facts and is not a claim of complete human editorial or visual review. Source
order is retained; unverified website positioning is not upgraded to verified.
Raw outputs and diagnostic manifests remain available in GitHub artifacts.

Only files in `chotuapp-rule804-files/manifest.json` whose identity and SHA256
match are copied to the existing local rclone remote. The destination folder is
`ChotuApp 20-10-2026 Fresh`. It contains XLSX files only. Copy is followed by rclone
checksum verification; same-name later outputs replace prior batch versions.
There is no remote-wide deletion and older dated folders are untouched. A local
lock prevents duplicate upload helpers. Existing 13 confirmed nonblank code
mappings were extracted from the reviewed 23-store batch; unknown codes remain
blank. No Drive credential or rclone configuration is sent to GitHub.

Cloud fetching and Rule 804 checks continue when the Windows helper closes.
Automatic Drive transfer needs that helper, its computer and its authenticated
rclone remote. The helper requests automatic-sleep prevention while active.
Ctrl+C stops uploads without cancelling cloud runs. Rerunning the same helper
reconnects to the stored batch and skips already verified uploads. A new fresh
batch requires a new state path/key; do not erase saved fetch checkpoints merely
to restart a failed upload. Failed/held stores are reported, never counted as
uploaded or described as complete.
