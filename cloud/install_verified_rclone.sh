#!/usr/bin/env bash
set -euo pipefail
# ID-preserving Drive moveid requires a newer release than Ubuntu 24.04 apt.
rclone_release=1.70.3
rclone_archive="rclone-v${rclone_release}-linux-amd64.zip"
rclone_stage=$(mktemp -d)
trap 'rm -rf "$rclone_stage"' EXIT
curl --retry 3 --fail --silent --show-error --location "https://downloads.rclone.org/v${rclone_release}/${rclone_archive}" --output "$rclone_stage/$rclone_archive"
curl --retry 3 --fail --silent --show-error --location "https://downloads.rclone.org/v${rclone_release}/SHA256SUMS" --output "$rclone_stage/SHA256SUMS"
awk -v archive="$rclone_archive" '$2 == archive || $2 == "*" archive {print}' "$rclone_stage/SHA256SUMS" > "$rclone_stage/expected.sha256"
test "$(wc -l < "$rclone_stage/expected.sha256")" -eq 1
(cd "$rclone_stage" && sha256sum --check expected.sha256)
unzip -q "$rclone_stage/$rclone_archive" -d "$rclone_stage"
sudo install -m 0755 "$rclone_stage/rclone-v${rclone_release}-linux-amd64/rclone" /usr/local/bin/rclone
rclone version
