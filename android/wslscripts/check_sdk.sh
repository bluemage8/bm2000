#!/bin/bash
SDK=/home/dapt/.buildozer/android/platform
echo "=== platforms ==="
ls "$SDK/platforms" 2>/dev/null
echo "=== build-tools ==="
ls "$SDK/build-tools" 2>/dev/null
echo "=== platform-tools/adb ==="
ls "$SDK/platform-tools/adb" 2>/dev/null && "$SDK/platform-tools/adb" version 2>/dev/null | head -1
echo "=== cmdline-tools ==="
ls "$SDK/cmdline-tools" 2>/dev/null
echo "=== gradle 8.14.3 present ==="
ls /home/dapt/.gradle/wrapper/dists/gradle-8.14.3-all/*/gradle-8.14.3/bin/gradle 2>/dev/null
echo "=== java ==="
/usr/lib/jvm/java-17-openjdk-amd64/bin/java -version 2>&1 | head -1
