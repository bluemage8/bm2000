# BridgeMaster2000 (bm2000) -- 桥牌大师 2000

[English](README.md)  ·  **简体中文 / Chinese**

[![Build Android APK](https://github.com/bluemage8/bm2000/actions/workflows/build-apk.yml/badge.svg)](https://github.com/bluemage8/bm2000/actions/workflows/build-apk.yml)

《桥牌大师 2000》的一个忠实重现 —— 这是 Windows 上一款经典的
「教你作为庄家打桥牌」的教学程序。本项目包含**三个版本**，三者共用
同一套经过验证的桥牌引擎：

* **桌面版**（Python 3 + Tkinter），从 [`run.py`](run.py) 启动。
* **网页版**（原生 JS + canvas），由 [`web/server.py`](web/server.py) 提供，
  把原先 794×547 的“窗口”等比缩放以适配浏览器窗口。
* **安卓版**（Kotlin + WebView），位于 [`android/`](android/)，由
  **GitHub Actions** 自动构建 —— 见下方[安卓 App](#安卓-app)。

相同的 5 个关卡、相同的约 530 副牌例、相同的游戏模型、相同的专家讲解，
以及相同的 **完成 / 未成（DEAL / FAILED）** 结算弹窗。

> **范围 / 法律说明。** 本项目是通过研究该程序的行为来实现的，并附带由
> 原程序提取的*牌例数据*和*帮助文件*，以保证玩法真实一致。原始程序
> **`bm2000.exe` 并未包含**在本项目中 —— 它属于专有软件，故刻意排除。
> [`winexe/hands`](winexe/hands) 中的数据仅用于让本仓库的代码可以运行，
> 并能在实现与原版之间进行对照验证。

---

## 游戏内容

你打 **庄家 = 南家** + **明手 = 北家**。电脑打 **防家 = 东家 + 西家**
（西家领出）。你唯一的目标是拿到完成定约所需的墩数；**超额完成没有额外
收益**。

* 你同时打 **北家** 和 **南家** 两手牌。
* 电脑自动打东家/西家的防守，采用标准防守约定（4 张以上出第四小、双张
  出大、仅三张裸门出小；跟牌；合理时吃张）。
* **强制跟牌**：只能从实际轮到的那个位置出牌（另一手的牌不可点击、不会
  高亮）。
* 打满 5 墩后可以**摊牌（claim）**；可以播放专家的「桥牌讲解（bridge
  movie）」、逐步推进，或**悔棋**（撤回上一张牌）。

---

## 语言：中 / 英

**网页版**界面为中/英双语，会**根据浏览器/终端语言自动切换**（中文浏览器
打开即为中文界面）；可用右上角 **EN / 中文** 按钮手动切换，也可在网址后加
`?lang=en` / `?lang=zh` 强制指定。详见[网页版说明](web/README_ZH.md)。
（桌面版 `run.py` 目前为原版的英文界面。）

---

## 仓库结构

```
.
├── run.py                  # 桌面版入口（Tkinter 界面）
├── bm2000/                 # 共享的 Python 包 —— 真正唯一的引擎
│   ├── cards.py            #   Card / Deal 数据模型 + 校验
│   ├── script.py           #   .LIN 解牌/叫牌解析
│   ├── levels.py           #   关卡索引读取（winexe/hands/<n>）
│   ├── playgame.py         #   逐墩交互式打牌引擎
│   ├── replay.py           #   快速无人值守自动打牌（供测试）
│   ├── bidding.py          #   叫牌/定约 + 庄家判定
│   ├── contract.py         #   定约语义：所需墩数(阶数+6)、成局/满贯判定、得分
│   ├── engine.py           #   更上层的牌局执行器
│   ├── gui.py              #   Tkinter 界面（目录 + 打牌页 + 弹窗）
│   └── sound.py            #   音效存根
├── web/                    # 网页版
│   ├── server.py           #   纯标准库 HTTP 服务器（静态文件 + /api/deals）
│   ├── gen_deals.py        #   从 winexe/hands 生成 deals.json
│   ├── deals.json          #   预生成的牌表（530 副）
│   ├── index.html          #   页面（#stage 存目录 + 打牌视图）
│   ├── style.css           #   布局 + 自适应缩放 + 闪光结算弹窗
│   ├── app.js              #   打牌引擎 + canvas 渲染 + 缩放
│   ├── selftest.html       #   浏览器内冒烟测试
│   ├── README.md           #   网页版使用/部署说明（英文）
│   └── README_ZH.md        #   网页版使用/部署说明（中文）
├── android/                # 安卓 App（Kotlin + WebView，详见 android/README.md）
│   ├── settings.gradle     #   Gradle 工程
│   ├── app/src/main/assets #   打包进去的网页版 + deals.json/deals.js
│   └── app/src/main/java/.../MainActivity.kt   # WebView 壳 + 数据桥接
├── .github/workflows/      # GitHub Actions：自动构建 APK（见「安卓 App」）
└── winexe/                 # 从原版提取的数据（不含 .exe）
    ├── hands/              #   5 个关卡的牌例数据（游戏主体）
    └── BM2000.HLP          #   原程序的帮助/说明文件
```

---

## 环境要求

* **桌面版：** Python **3.8+** 并带 `tkinter`（多数环境已内置；Linux 下：
  `sudo apt install python3-tk`）。
* **网页版：** Python **3.6+**（纯标准库，无第三方依赖），**或**任意静态
  服务器。需要使用现代浏览器（Chrome/Edge/Firefox）。

两个版本都**不需要**第三方 Python 库。

---

## 运行桌面版

```bash
cd <本仓库目录>

# 启动 Tkinter 界面（开场动画 → 目录 → 选一副牌）
python run.py

# 直接打开某一关卡/某一副牌
python run.py 1 A1

# 仅列出关卡及其牌例（不启动界面）
python run.py list
```

`run.py` 会从 `./winexe/hands`（已随仓库提供）读取牌例数据，从
`./winexe/BM2000.HLP` 读取帮助。

### 桌面版控件（打牌屏）

| 工具栏按钮 | 作用 |
|----------------|--------|
| First / Prev / Next / Last | 跳到第一 / 上一副 / 下一副 / 最后一副 |
| Replay deal | 从头重打当前这副 |
| Step | 打出下一张（自动防守）牌 |
| Take back | 悔棋（撤回上一张） |
| Claim | 声明定约完成（≥5 墩后可用） |
| Movie / 1st / Prev / Next / Last | 打开专家的「桥牌讲解」并翻页 |
| Big / Small | 切换大 / 小牌 |
| Show / Hide | 切换打出的牌是否保留可见 |
| Sound on/off | 切换音效 |
| Help | 打开帮助 |

点击南家/北家手里被**高亮**的牌即可打出（只有轮到那一手时才可出合法牌）。
桌面窗口可自由拉伸，牌桌与卡牌会随之等比缩放。

---

## 运行网页版

网页版**无需安装** —— 它就是静态文件外加一个很小的标准库服务器（同时通过
`/api/deals` 提供牌表）。

```bash
cd web

# 默认端口 8321，绑定 0.0.0.0（内网可达）
python server.py            # -> http://<你的IP>:8321（localhost 也行）

# 或自定义端口
BM2000_PORT=9000 python server.py
# 或者
python server.py 9000
```

然后在浏览器打开 **http://localhost:8321**（或 **http://<服务器IP>:8321**）。
页面会把 794×547 的窗口等比缩放以适配浏览器，保持宽高比，以适配任意窗口
尺寸 / 手机。

> `deals.json` **已生成**并随仓库提交，网页版开箱即玩。如需重新生成
> （例如改动了数据）：
>
> ```bash
> python web/gen_deals.py    # 根据 winexe/hands 重写 web/deals.json
> ```

### 网页版控件

* **点击**南家/北家手里被高亮的牌即可打出（只有轮到那一手时才可出合法牌；
  强制跟牌；缺门时可吃张/垫牌）。防家自动领出并出牌。
* 工具栏：**重放**、**悔棋**、**单步**、**摊牌**、**讲解**（播放专家
  解说）、**放大 / 缩小**。
* 结算：不断闪动的 **完成**（成）/ **未成**（失）弹窗显示得分，并提供
  **重新开始 / 显示答案 / 下一副** 按钮。

### 浏览器内自检

打开 `web/selftest.html`（通过 **http://localhost:8321/selftest.html** 提供）。
它会载入全部 530 副牌、把抽样牌例打到结束，并验证自适应缩放。数据与引擎
正常时会打印 **`RESULT: ALL PASS`**。

---

## 安卓 App

安卓版（`android/`）是网页版的原生 **Kotlin + WebView** 壳：WebView 加载
打包进 APK 的网页版（`index.html` / `app.js` / `style.css`），牌例数据离线
内置（`assets/deals.json` + `deals.js` 预加载回退），794×547 牌桌自适应缩放到
屏幕（横屏）。玩法与网页版完全一致。

### 直接拿 APK（无需自己构建）

APK 由 **GitHub Actions**（`.github/workflows/build-apk.yml`）自动构建：

* **每次 push 到 `main`** 都会产出一个新的 debug APK，可在该次运行的页面
  下载 `bm2000-debug` 产物（[Actions](https://github.com/bluemage8/bm2000/actions)）。
* **打版本 tag**（如 `git tag v1.0 && git push origin v1.0`）会自动创建一个
  **GitHub Release** 并附上 APK —— 到 [Releases](https://github.com/bluemage8/bm2000/releases)
  下载。

安装：把 APK 拷到手机上打开即可（按需允许「允许安装未知来源应用」）。
要求 Android 7.0+（API 24）。

### 自己构建

**不需要**原来的 WSL 工具链 —— 标准 JDK 17 + Android SDK 即可。仓库未附带
Gradle wrapper jar，所以用系统 `gradle`（或 Android Studio）：

```bash
cd android

# 一次性：本机没有 wrapper jar 时先生成（需 PATH 上有 gradle）
gradle wrapper --gradle-version 8.7

# 构建 debug APK（可直接安装）
gradle :app:assembleDebug
#   -> app/build/outputs/apk/debug/app-debug.apk
```

前置条件：**JDK 17**、**Android SDK**（compileSdk 34）、**Gradle 8.7+**。
`applicationId` = `com.bm2000.bridge`；`minSdk 24` / `targetSdk 34`。

> 也可直接用 **Android Studio** 打开 `android/` 目录后 Run 到设备。
> **release**（上架/签名）版本需要签名密钥：在 `app/build.gradle` 配置
> `signingConfigs`，或用 Android Studio 的 *Build ▸ Generate Signed APK*。
> CI 产出的是 debug 签名 APK。

完整说明见 [`android/README.md`](android/README.md)。

---

## 游戏规则（两版通用）

桌面版与网页版都委托给同一套规则，行为一致：

* **进墩判定** — 若非主花色领出时有人出主牌，则取其中最大的主牌；否则取
  领出花色中最大的牌。
* **合法出牌** — 若持有领出花色则必须跟牌；否则可吃张（出主牌）或垫牌。
* **轮转领出** — 进墩者领出下一墩；我方只能从实际轮到的北/南手里出牌。
* **结果** — 北家 + 南家拿到的墩数 ≥ **阶数 + 6** 即为*完成*（1 阶定约需
  7 墩、4 阶高花需 10 墩、7 阶大满贯需全部 13 墩）；否则为*未成*。结算弹窗
  会给出得分：墩分（低花 20/阶、高花 30/阶、无将 40 + 30·(阶−1)），达到成局
  线（3NT / 4♥ / 4♠ / 5♣ / 5♦）加**成局**奖分，6 阶加**小满贯**奖分、7 阶加
  **大满贯**奖分，未成时按差几墩罚分。

防务 AI 在两个版本中使用同一套**约定**（并非深度对抗搜索）。这是文档中
说明的、有意的简化。

---

## 部署网页版到服务器

`web/` 中随附一个 nohup 启动脚本。在装有 Python 3.6+ 的 Linux 机器上的
最小步骤：

```bash
# 1. 把 web/ 拷贝过去（它自包含：静态文件 + deals.json + server.py）
scp -r web/* user@host:/opt/bm2000/

# 2. 在目标机器上启动，绑定 0.0.0.0:8321
cd /opt/bm2000
BM2000_HOST=0.0.0.0 nohup python3 server.py 8321 >> server.out 2>> server.err &

# 3. 在防火墙放开该端口，例如 firewalld (CentOS):
sudo firewall-cmd --permanent --add-port=8321/tcp && sudo firewall-cmd --reload
```

然后可从内网 **http://<机器IP>:8321** 访问。若希望重启后仍然可用，请改用
systemd 服务而不是 nohup。完整部署说明见 [`web/README.md`](web/README.md)。

> `web/server.py` 按 Python **3.6+** 编写（后置了 `ThreadingHTTPServer`，
> 避开 3.7 专有语法），默认绑定 `0.0.0.0` 以便内网访问（可用
> `BM2000_HOST` / `BM2000_PORT` 覆盖）。

---

## 校验本重现

共享引擎由自动化检查覆盖：

* **52 张守恒** — 任意一副完整自动打完后，全部 52 张牌落入 13 墩，
  四手牌均为 0 张。
* **跟牌 / 轮到限制** — 只接受轮到那一手的合法牌；未轮到或未跟领出花色
  的出牌会被拒绝。
* **进墩判定一致性** — 随机的牌盘已与独立参考实现对照（100% 一致）。
* **网页自检** — `web/selftest.html` 会在浏览器里重打全部 530 副的抽样
  并断言各项不变量。

---

## 数据说明

* 5 个技能关卡来自 `winexe/hands/<1..5>/{Index,Data}`。
* 原始数据中有 5 条记录的 `md` 值损坏、无法构成合法的 52 张牌盘；两个
  版本**都会自动跳过**这些记录，最终保留 **530 副可玩**牌例
  （L1: 182, L2: 95, L3: 94, L4: 94, L5: 65）。
* `.LIN` 文件名在各关卡间循环重用（例如每个关卡都有 `A1.LIN` 但内容不同），
  因此牌例用 `<分组>-<序号>` 代码（A-1, B-12, …）来标识，而非文件名。

---

## 许可

这是一个用于个人与教学的**研究 / 重现**项目。它不包含原始专有可执行文件。
牌例数据与帮助文件仅用于使本仓库代码可以运行、可以验证。请尊重原软件版权
—— 不要再次分发原始的 `bm2000.exe`。
