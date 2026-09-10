#!/bin/bash
echo "=== search for platforms;android-34 / android.jar ==="
find /home/dapt /root /opt /usr -maxdepth 8 -name "android.jar" 2>/dev/null | head
echo "=== search for aapt2 / aapt ==="
find /home/dapt /root /opt /usr -maxdepth 8 -name "aapt2" 2>/dev/null | head
find /home/dapt /root /opt /usr -maxdepth 8 -name "aapt" 2>/dev/null | head
echo "=== search for platform-tools/adb ==="
find /home/dapt /root /opt /usr -maxdepth 8 -path "*platform-tools/adb" 2>/dev/null | head
echo "=== search for sdkmanager ==="
find /home/dapt /root /opt /usr -maxdepth 8 -name "sdkmanager" 2>/dev/null | head
echo "=== buildozer android platform dir ==="
ls -la /home/dapt/.buildozer/android/platform 2>/dev/null
echo "=== env vars of dapt (profile) ==="
grep -rE "ANDROID|JAVA_HOME" /home/dapt/.bashrc /home/dapt/.profile /home/dapt/.bash_profile 2>/dev/null | head
echo "=== local.properties anywhere ==="
find /home/dapt -maxdepth 4 -name "local.properties" 2>/dev/null | head
echo "DONE"
