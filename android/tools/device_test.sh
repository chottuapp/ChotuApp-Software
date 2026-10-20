#!/usr/bin/env bash
set -euo pipefail
cd android
gradle connectedDebugAndroidTest --stacktrace 2>&1 | tee device.log
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.chotuapp.studio/com.chotuapp.mobile.LoginActivity
sleep 4
adb shell screencap -p /sdcard/chotuapp.png
adb pull /sdcard/chotuapp.png dashboard.png
