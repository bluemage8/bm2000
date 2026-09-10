#!/bin/bash
# Build the bm2000 Android app (Kotlin + WebView) using the EXISTING dapt toolchain.
# Stage project -> run gradle :app:assembleDebug -> copy APK back to E:.
set -e

PROXY=http://172.16.127.58:8282
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export PATH="$JAVA_HOME/bin:$PATH"
export ANDROID_SDK_ROOT=/home/dapt/.buildozer/android/platform/android-sdk
export ANDROID_HOME=/home/dapt/.buildozer/android/platform/android-sdk
export GRADLE_USER_HOME=/home/dapt/.gradle
export http_proxy="$PROXY"
export https_proxy="$PROXY"
export ALL_PROXY="$PROXY"
export PIP_BREAK_SYSTEM_PACKAGES=1

SRC=/mnt/e/workspace/bm2000/android
DST=/home/dapt/bm2000
LOG=/home/dapt/bm2000-build.log

echo "=== stage project ==="
rm -rf "$DST"
mkdir -p "$DST"
cp -r "$SRC/." "$DST/"
# point local.properties at the existing SDK
printf 'sdk.dir=%s\n' "$ANDROID_SDK_ROOT" > "$DST/local.properties"
echo "sdk.dir -> $ANDROID_SDK_ROOT"
ls -la "$DST/app/src/main/assets" | head

echo "=== sdk check ==="
ls "$ANDROID_SDK_ROOT/platforms" 2>/dev/null
ls "$ANDROID_SDK_ROOT/build-tools" 2>/dev/null
"$ANDROID_SDK_ROOT/platform-tools/adb" version 2>/dev/null | head -1 || echo "no adb in sdk (ok, using windows adb)"

echo "=== gradle assembleDebug ==="
cd "$DST"
/usr/local/bin/gradle :app:assembleDebug --no-daemon --console=plain 2>&1 | tee "$LOG"

echo "=== locate apk ==="
APK=$(ls -1 "$DST/app/build/outputs/apk/debug/"*.apk 2>/dev/null | head -1)
if [ -n "$APK" ] && [ -f "$APK" ]; then
  echo "APK_FOUND: $APK"
  cp "$APK" /mnt/e/workspace/bm2000/android/bm2000-debug.apk
  ls -la /mnt/e/workspace/bm2000/android/bm2000-debug.apk
  echo "BUILD_OK"
else
  echo "BUILD_FAILED (no apk found)"
  echo "--- tail of log ---"
  tail -n 40 "$LOG"
fi
