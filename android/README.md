# Bridge Master 2000 — Android App

桥牌大师 2000 的安卓 App。采用 **Kotlin + WebView** 方案：
原生壳（全屏横屏、沉浸模式）加载打包在 `assets` 里的网页版
（`index.html` / `app.js` / `style.css`），牌例数据 `deals.json`
随 APK 分发、离线可玩。

## 工作原理

- 原生 `MainActivity` 创建 WebView，`loadUrl("file:///android_asset/index.html")`。
- 网页版原本从 `/api/deals` 拉牌表（由 `web/server.py` 提供）。
  App 里两条通道保证能拿到数据：
  1. **WebViewClient.shouldInterceptRequest** — 拦截 `/api/deals`，
     直接从 `assets/deals.json` 返回响应（主通道）。
  2. **`deals.js`** — 把 `deals.json` 内容预加载为
     `window.__DEALS__`，`app.js` 在 fetch 失败时回退读取（双保险）。
- 牌桌 794×547 固定尺寸，`app.js` 的 `fitStage()` 用 CSS transform 等比
  缩放到屏幕，因此手机/平板都自适应。

## 目录结构

```
android/
├── settings.gradle / build.gradle / gradle.properties
├── gradle/wrapper/gradle-wrapper.properties
└── app/
    ├── build.gradle / proguard-rules.pro
    └── src/main/
        ├── AndroidManifest.xml
        ├── java/com/bm2000/bridge/MainActivity.kt
        ├── res/                # 主题 + 启动图标
        └── assets/             # 网页版静态文件 + deals.json/deals.js
```

## 构建

前置条件：

- JDK 17
- Android SDK（compileSdk 34）
- 已设置 `ANDROID_HOME` / `ANDROID_SDK_ROOT`（或 SDK 装在默认位置）
- 本机已有 Gradle（用于首次生成 wrapper jar），或直接从 Android Studio 打开

步骤：

```bash
cd android

# 1. 若本机装了 gradle，先生成 wrapper（一次即可）
gradle wrapper --gradle-version 8.7

# 2. 构建 release APK
./gradlew :app:assembleRelease

# 2b. 或构建 debug APK（可直接安装到设备）
./gradlew :app:assembleDebug

# 3. 安装到已连接的设备
./gradlew :app:installDebug
```

产物路径：

- `app/build/outputs/apk/debug/app-debug.apk`
- `app/build/outputs/apk/release/app-release-unsigned.apk`

> release 需签名后才能上架/正式安装。可用 Android Studio 的
> Build > Generate Signed Bundle / APK 生成签名版本，或配置
> `signingConfigs`。

## 用 Android Studio 打开（推荐）

1. Android Studio → Open → 选择 `android/` 目录
2. 等待 Gradle 同步
3. Run ▶ 到已连接设备/模拟器（需 minSdk 24，即 Android 7.0+）

## 重新生成牌例数据

如果改动了 `winexe/hands` 数据：

```bash
# 重新生成 web/deals.json
python web/gen_deals.py

# 把它同步进 App 的 assets
cp web/deals.json android/app/src/main/assets/deals.json

# 重新生成 deals.js（预加载回退用）
python -c "import json,io; d=open('android/app/src/main/assets/deals.json',encoding='utf-8').read(); open('android/app/src/main/assets/deals.js','w',encoding='utf-8').write('window.__DEALS__ = '+d+'\n')"
```

## 包名 / 版本

- `applicationId` = `com.bm2000.bridge`
- `minSdk` 24 / `targetSdk` 34 / `versionName` 1.0

如需改名或改图标，修改 `app/build.gradle` 与 `res/` 下资源即可。
