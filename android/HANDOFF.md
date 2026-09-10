# Bridge Master 2000 — Android App 构建/调试交接说明

> 给后续 agent / 会话的权威 handoff。读完即可接续。
> 更新：2026-09-10 首次打包 + MI 5X 真机部署成功。

## 是什么

把 `E:\workspace\bm2000\web\`（原生 JS + canvas 网页版，530 副桥牌）用
**Kotlin + WebView** 包成安卓 App。原生壳全屏横屏、沉浸模式，加载打包在
`assets` 里的网页版，牌例 `deals.json` 离线内置。玩法与网页版完全一致。

工程目录：`E:\workspace\bm2000\android\`

## 数据加载（两条通道，都在 file:// 下生效）

网页版原本 `fetch("/api/deals")`（由 `web/server.py` 提供）。App 里：
1. `MainActivity.WebViewClient.shouldInterceptRequest` 拦截 `/api/deals`，
   从 `assets/deals.json` 返回响应（主通道）。
2. `deals.js`（`window.__DEALS__ = <deals.json 内容>`）作为 `<script>` 预加载，
   `app.js` 在 fetch 失败时回退读 `window.__DEALS__`。
   **实测 MI 5X 上走的是回退通道**：logcat 见
   `Fetch API cannot load file:///api/deals. URL scheme must be http/https`，
   随后 title 变 `BM2000_OK deals=530`。两通道都在，保险。

## 构建（WSL 现成工具链，不用装任何东西）

- WSL `Ubuntu`（26.04），用户 `dapt`，**JDK17** `/usr/lib/jvm/java-17-openjdk-amd64`。
- **Gradle 8.14.3** 已在 `/home/dapt/.gradle/wrapper/dists/gradle-8.14.3-all/.../bin/gradle`，
  已软链 `/usr/local/bin/gradle`。
- **Android SDK** 在 `/home/dapt/.buildozer/android/platform/android-sdk/`
  （platform-34 + build-tools 34.0.0/37.0.0 + platform-tools + adb 全齐）。
  **注意路径多一层 `android-sdk`**（不是 handoff 旧文档写的 `platform/`）。
- 构建脚本：`E:\workspace\bm2000\android\wslscripts\build_debug.sh`
  - stage 工程到 `/home/dapt/bm2000`，写 `local.properties`（sdk.dir 指向上面）
  - 设代理 `http://172.16.127.58:8282`（dl.google 直连也通）
  - `gradle :app:assembleDebug --no-daemon`
  - 成功自动 `cp` APK 到 `E:\workspace\bm2000\android\bm2000-debug.apk`
- 启动（前台，~17s）：
  ```
  wsl -u dapt -e /bin/bash /mnt/e/workspace/bm2000/android/wslscripts/build_debug.sh
  ```
  看 `BUILD SUCCESSFUL` + `APK_FOUND`。
- **陷阱**：PowerShell 5.1 会破坏内联 `$`/`$( )`/here-doc/嵌套引号/`|` 管道。
  **一律写 .sh/.py/.js 到持久目录再 `wsl -u dapt -e /bin/bash <path>` 跑**，
  不要 `wsl ... | grep`（grep 在 PowerShell 侧）。

## build.gradle 踩的 3 个坑（已修，别再退回）

1. **必须加 `org.jetbrains.kotlin.android` 插件**（app + 根 build.gradle 都要，
   版本 1.8.22）。只写 `com.android.application` 会不编译 Kotlin →
   `ClassNotFoundException: MainActivity`。
2. **JVM target 对齐**：`kotlinOptions { jvmTarget = '1.8' }` +
   `compileOptions` 1.8。否则 `compileDebugKotlin` 报
   "jvm target compatibility should be set to the same"（Kotlin 默认 17 vs Java 1.8）。
3. **kotlin-stdlib 冲突**：appcompat:1.7.0 传递 kotlin-stdlib-jdk7/jdk8:1.6.21，
   与 AGP 带的 kotlin-stdlib 1.8.x 重复类 → `checkDebugDuplicateClasses` 失败。
   在 app/build.gradle 加：
   ```
   configurations.all { resolutionStrategy {
     force 'org.jetbrains.kotlin:kotlin-stdlib:1.8.22'
     force 'org.jetbrains.kotlin:kotlin-stdlib-jdk7:1.8.22'
     force 'org.jetbrains.kotlin:kotlin-stdlib-jdk8:1.8.22' } }
   ```
4. **主题必须 AppCompat**：`AppCompatActivity` 要求 `Theme.AppCompat.*`，
   用 `android:Theme.Material` 会 `IllegalStateException: need Theme.AppCompat`。
   已用 `Theme.AppCompat.NoActionBar`。

## 真机部署（MI 5X）

- 手机：小米 MI 5X，adb 序列号 **`881ede900404`**，Android 7.1.2，
  横屏物理 1920×1080（CSS 像素 640×360，density 3）。
- **本机连了两台设备**（MI 5X + 一台 `127.0.0.1:52293` cutefish_k6），
  **所有 adb 命令必须 `-s 881ede900404` 指定序列号**，否则 "more than one device"。
- adb（Windows）：`E:\gauto\pt\platform-tools\adb.exe`（v37）。
  路径无空格，但 PowerShell 里用 `cmd /c ""E:\gauto\pt\platform-tools\adb.exe" ..."` 包双引号。
- 安装：
  ```
  cmd /c ""E:\gauto\pt\platform-tools\adb.exe" -s 881ede900404 install -r -t "E:\workspace\bm2000\android\bm2000-debug.apk""
  ```
  首次可能 `INSTALL_FAILED_USER_RESTRICTED`（MIUI USB 安装限制）→ 手机端点
  「允许」，或 设置→开发者选项→开「USB 调试（安全设置）」。本次已成功。
- 启动：
  ```
  cmd /c ""E:\gauto\pt\platform-tools\adb.exe" -s 881ede900404 shell am start -n com.bm2000.bridge/.MainActivity"
  ```
  **entrypoint 是 `.MainActivity`**（不是 Kivy 那个 PythonActivity，本工程是纯 Kotlin）。
  包名 `com.bm2000.bridge`。

## 验证手段（MI 5X 截图抓不到 WebView！）

**MI 5X 的 `screencap` 抓 WebView 硬件层内容不全**（修复前截图恒 35431 字节
= 纯背景空白；修复后 15295 字节 = 有内容）。所以**别靠截图判断渲染**，用：

1. **logcat 读 title**：`app.js` 初始化末尾把状态写 `document.title`，
   `MainActivity` 的 `WebChromeClient.onReceivedTitle` 打 `Log.i("BM2000","title="+...)`。
   正常应见：
   ```
   I/BM2000: title=BM2000_OK deals=530 lvbtns=5 rows=182 win=640x360 stage=523x360@x59,y0 tocHidden=false
   ```
   `deals=530`=牌表全加载，`lvbtns=5 rows=182`=DOM 建了 5 关卡按钮+182 牌例，
   `stage=523x360@x59,y0`=stage 完整居中可见（y0 顶对齐、高占满），`tocHidden=false`=目录页显示。
2. **截图字节数变化**：`screencap` 后看文件 size，从恒值变化 = 内容变了。
   配 tesseract（WSL 已装 `tesseract-ocr` + `chi_sim`）OCR，能读到零星 UI 文字（如 "EN" 按钮）。
3. **adb 模拟点击被 MIUI 拒**（`Permission denied: injecting event`），
   无法用 `input tap` 验证交互。要测交互得让用户手动点，或用
   `?level=1&deal=0` URL 参数自动开牌（app.js 支持）。

## 修过的渲染 bug（本次核心）

### Bug 1（真正根因）：chromium 86 不支持 `inset` 简写 → TOC 塌陷
症状：App 启动正常、数据全加载（deals=530）、EN/中文 按钮可见（`position:fixed`），
但关卡列表 / 牌例区**完全不可见**。
根因（用 `__dumpGeom` 诊断 JS 读 `getBoundingClientRect` 证实）：
```
#toc      {60,1   0x0}      ← TOC 容器布局盒 0×0！
#lvcol    {62,3   71x5}     ← 关卡按钮列高 5px
#dealRows {137,5  0x2396}   ← 牌例区宽 0
```
`.view { position:absolute; inset:0 }` 的 **`inset` 简写在 MI 5X 的 WebView
（chromium ~86，Android 7.1）上不生效** → `#toc` 没有 top/left/right/bottom →
绝对定位无锚点 → 布局盒塌陷 0×0 → 子元素全塌。`#langbar` 用显式 `top/right`
所以正常。
修复：把 style.css 里**所有 `inset:0` 改成显式 `top:0;left:0;right:0;bottom:0`**
（共 4 处：#viewport / .view / #board / .modal）。
修复后 GEOM：`#toc 521x359`、`#lvcol 71x339`、`#dealRows 440x2396`、`.lvbtn 66x22` 全部正常。
**教训：Android 7.1 的 WebView 是 chromium 86，CSS 新特性（`inset`、`gap`、
`:is()` 等）要逐个验证，能用传统属性就别用简写。**

### Bug 2：视口 + fitStage 裁切
`<meta viewport width=device-width>` 在 MI 5X file:// 下算出 640×360 CSS 像素
（正常，density 3）。`fitStage()` 原 `transform:scale()` + `transform-origin:center`
在 stage 布局盒(547高) 与视口(360高) 不匹配时裁切。
修复：`#viewport` `overflow:hidden`；`#stage` `position:absolute;left:0;top:0;transform-origin:top left`；
`fitStage()` 改 `transform: translate(tx,ty) scale(s)`，`s=min(vw/794,vh/547)`（去掉 3x 上限），
tx/ty 居中。修复后 stage 523×360 完整居中（x59,y0）。
canvas（board）用 `clientWidth/clientHeight` 自适应 + `getBoundingClientRect` 算点击，
stage 尺寸变化不影响 canvas。

## 诊断工具（留在代码里，排查时用）

- `app.js` 末尾 `window.__dumpGeom()`：读 `#stage/#toc/#lvcol/#dealRows/.lvbtn/#langbar`
  的 `getBoundingClientRect` + computed style 写进 `document.title`（GEOM ...）。
  **这是看真实 DOM 布局的唯一可靠手段**（MI 5X screencap 抓不到 WebView 层）。
- `app.js` `window.__exportStagePNG()`：把 TOC 手动重画成 canvas 导出 base64 →
  `AndroidBridge.savePng()` → native 写 `getExternalFilesDir/bm2000_stage.png`。
  可 `adb pull` 出来 OCR（注意：这是 JS 重画的，不是真实像素，仅验证数据流）。
- `MainActivity` `WebChromeClient.onReceivedTitle` 打 `Log.i("BM2000","title="+...)`，
  `onPageFinished` 后 1.5s 调 `__dumpGeom`+`__exportStagePNG`。
- 读：`adb -s 881ede900404 logcat -d | findstr "title="`。

## 文件地图

- `E:\workspace\bm2000\android\`：安卓工程（settings/build/gradle.properties + app/）
- `app/src/main/java/com/bm2000/bridge/MainActivity.kt`：WebView 壳 + 数据桥接 + title 日志
- `app/src/main/assets/`：index.html / app.js / style.css / deals.json / deals.js
  （**独立副本**，改了要重新 build；`web/` 原始目录未动）
- `app/src/main/res/values/styles.xml`：`Theme.AppCompat.NoActionBar` 全屏黑
- `app/src/main/res/mipmap-anydpi-v26/` + `drawable/ic_launcher_fg.xml`：黑桃启动图标
- `wslscripts/build_debug.sh`：主构建脚本
- `wslscripts/check_sdk.sh` / `find_sdk.sh`：SDK 探测（诊断用）
- `E:\workspace\bm2000\android\bm2000-debug.apk`：最新 APK（~4.6MB）

## 遗留 / 注意

- release 需签名（Android Studio Generate Signed APK 或配 signingConfigs）。
- 改了 `winexe/hands` 数据要重跑 `python web/gen_deals.py` 再同步 deals.json + 重新生成 deals.js（见 android/README.md）。
- app.js 里留了诊断 title 写入（BM2000_OK...），正式上线前可删，但留着无害且方便排查。
- 本机第二台设备 `127.0.0.1:52293`（cutefish_k6）来源未知，adb 务必带 `-s`。
