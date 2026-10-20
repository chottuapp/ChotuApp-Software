#!/usr/bin/env bash
set -euo pipefail
cd android
gradle connectedDebugAndroidTest --stacktrace 2>&1 | tee device.log
adb shell am start -n com.chotuapp.mobile/.MainActivity
sleep 4
adb shell screencap -p /sdcard/chotuapp.png
adb pull /sdcard/chotuapp.png dashboard.png
