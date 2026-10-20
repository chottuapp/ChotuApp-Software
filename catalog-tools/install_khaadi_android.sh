#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
mobile_data_dir="$HOME/ChotuAppMobile"
mkdir -p "$mobile_data_dir"
command -v termux-wake-lock >/dev/null && termux-wake-lock || true
pkg update -y
pkg install -y proot-distro curl
if [ ! -d "$PREFIX/var/lib/proot-distro/installed-rootfs/ubuntu" ]; then
  proot-distro install ubuntu
fi
proot-distro login ubuntu -- bash -lc 'set -e; apt-get update -qq; apt-get install -y python3 python3-venv python3-tk curl ca-certificates gh; if [ ! -x /root/chotu-venv/bin/python ]; then python3 -m venv /root/chotu-venv; fi'
proot-distro login ubuntu -- /root/chotu-venv/bin/pip install requests beautifulsoup4 openpyxl
# A real, logged-in GitHub CLI is needed for heartbeat and final workbook upload.
if ! proot-distro login ubuntu -- gh auth status >/dev/null 2>&1; then
  proot-distro login ubuntu -- gh auth login --hostname github.com --git-protocol https --web
fi
proot-distro login ubuntu -- curl --fail --location --max-time 60 --silent --show-error 'https://raw.githubusercontent.com/chottuapp/ChotuApp-Software/main/catalog-tools/khaadi_mobile.py' --output /root/khaadi_mobile.py
printf '%s\n' 'Android worker starting. Keep Termux active and internet connected; saved files remain in ~/ChotuAppMobile.'
proot-distro login --bind "$mobile_data_dir:/chotuapp-data" ubuntu -- /root/chotu-venv/bin/python /root/khaadi_mobile.py
