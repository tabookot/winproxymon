[English](README.md) | [简体中文](README.zh.md) | [Русский](README.ru.md)

# 🛡️ WinProxyMon (Windows 代理与 Tor 监控器)

WinProxyMon 是一款适用于 Windows (7/8/10/11) 的轻量级、无干扰系统托盘应用程序，旨在监控代理服务器的可用性。它使用 Python 和 PyQt5 构建，提供实时视觉反馈、智能通知以及强大的内置 Tor 服务管理器。

无论您是在运行简单的 SOCKS5 代理还是复杂的 Tor 网桥设置，WinProxyMon 都能确保您随时了解连接的确切状态，而无需离开桌面或在全屏游戏时被打扰。

> *作者团队 — GLM, GPT.*

## ✨ 主要特性

* **多代理监控：** 同时监控数量不限的代理（支持 SOCKS4/5、HTTP、HTTPS）。
* **智能三层诊断：** 不仅仅是简单的 Ping。它会检查本地互联网、代理端口可用性以及实际的 HTTP 出口能力。
* **智能全屏检测：** 当运行全屏应用程序（如游戏或视频播放器）时，自动抑制弹窗通知。
* **可视化状态图标：** 直观查看您的代理是否在线（绿色）、卡住/无出口（黄色）或离线（红色）。
* **内置 Tor 服务管理器：** 专用图形界面，用于安装、启动、停止和重启 Tor Windows 服务。
* **网桥获取与应用工具：** 自动从 TorProject.org 获取最新的 `obfs4` 网桥，并安全地将其写入您的 `torrc` 文件。
* **开机自启支持：** 轻松配置应用程序随 Windows 启动。

---

## 🧠 工作原理（诊断逻辑）

与基本的 Ping 监控器不同，WinProxyMon 使用三层检查系统来为您提供代理健康状况的准确图景：

1. **本地互联网检查：** 直接连接到 `8.8.8.8:53`。如果失败，说明您的电脑没有本地互联网连接。状态：🔴 **OFFLINE (NO LOCAL NET / 离线-无本地网络)**。
2. **TCP 端口检查：** 尝试连接代理的 IP 和端口。如果失败，说明代理软件（如 Tor）未运行或已崩溃。状态：🔴 **OFFLINE (PORT CLOSED / 离线-端口关闭)**。
3. **HTTP 出口检查：** 尝试通过代理加载网站。如果失败但端口已开放，说明代理正在运行但无法路由流量（例如 Tor 网桥已失效）。状态：🟡 **NO EXIT (无出口)**。
4. **成功：** 如果 HTTP 请求成功，说明代理功能完全正常。状态：🟢 **ONLINE (在线)**。

如果为代理分配了插件（如 `tor`），当发生 `NO EXIT` 状态时，应用程序将查询插件以获取详细的错误日志，并在托盘提示和日志中显示确切的 Tor 引导失败原因。

---

## 🌐 了解 `check_urls`

在您的 `winproxymon.ini` 配置文件中，有一个名为 `check_urls` 的设置。这是一个以逗号分隔的网站列表，应用程序使用它来验证流量是否可以成功退出代理。

**如何为此列表选择优质的 URL：**
1. **仅限纯文本：** URL 必须只返回 IP 地址，*不包含任何其他内容*。如果网站返回 HTML、JSON 或额外的文字，检查将失败或污染您的日志。（例如，`https://api.ipify.org` 只返回 `185.220.101.5`）。
2. **轻量级：** 使用快速、极简的 API。避免加载包含大量脚本的重型网页。
3. **无 Cloudflare/Tor 屏蔽：** 许多标准网站会屏蔽 Tor 出口节点。提供的默认值是已知对 Tor 友好的网站。
4. **冗余备份：** 应用程序会按顺序检查它们。如果第一个 URL 宕机，它会尝试下一个。这可以防止在单个检查 IP 的网站离线时出现错误的“NO EXIT”警报。

**推荐的默认值：**
```ini
check_urls = https://api.ipify.org, https://checkip.amazonaws.com, https://ident.me
```

---

## 🧅 什么是 Tor Expert Bundle？

如果您只是想匿名浏览网页，您可以使用 **Tor Browser（Tor 浏览器）**。但如果您希望其他应用程序（或整个系统）通过 Tor 路由流量，您就需要 **Tor Expert Bundle（Tor 专家包）**。

Tor Expert Bundle 是纯粹的 Tor 守护进程，没有任何图形界面。它在后台静默运行，作为一个进程（或理想情况下作为 Windows 服务），并暴露一个 SOCKS5 代理（通常在 `127.0.0.1:9050`）。

WinProxyMon 正是为了管理这个专家包而设计的。它可以将 Tor 守护进程安装为稳固的 Windows 服务，配置其网桥，读取其日志，并监控其 SOCKS5 端口。

---

## 🚀 安装与设置

### 从源码运行 (Python 3.8+)
1. 克隆仓库：
   ```bash
   git clone https://github.com/tabookot/winproxymon.git
   cd winproxymon
   ```
2. 安装依赖项：
   ```bash
   pip install -r requirements.txt
   ```
3. 运行应用程序：
   ```bash
   python winproxymon.py
   ```

### 编译可执行文件 (PyInstaller)
要编译您自己的 `.exe`，请确保已安装 PyInstaller，然后使用提供的 `.spec` 文件以确保所有资源和插件被正确打包：
```bash
pyinstaller winproxymon.spec
```
编译后的可执行文件将位于 `dist/` 文件夹中。

---

## 🛠️ 完整指南：从零开始设置 Tor

按照以下步骤，将 Tor Expert Bundle 设置为由 WinProxyMon 管理的 Windows 服务。

### 第 1 步：下载 Tor Expert Bundle
1. 访问 Tor Project 官方下载页面：[Tor Expert Bundle](https://www.torproject.org/download/tor/)
2. 下载 Windows `.exe` 安装程序或 `.zip` 压缩包。
3. 将其解压到永久文件夹，例如：`C:\tor\tor\`（确保 `tor.exe` 位于此文件夹内）。

### 第 2 步：配置 WinProxyMon
1. 打开 WinProxyMon。
2. 右键点击托盘图标并选择 **Manage Proxies... (管理代理...)**
3. 点击 **Add (添加)**（或编辑默认代理）。
4. 填写详细信息：
   * **Name (名称):** `Tor Local`
   * **Host (主机):** `127.0.0.1`（如果 Tor 在另一台电脑上，则填写局域网 IP）
   * **Port (端口):** `9050`（默认 Tor SOCKS5 端口）
   * **Protocol (协议):** `socks5`
   * **Plugin (插件):** 从下拉菜单中选择 `tor`。
5. 点击 **Save (保存)**。

### 第 3 步：通过插件界面配置 Tor 服务
1. 在“管理代理”窗口中，点击 **Configure Plugin... (配置插件...)** 按钮。
2. 在“Tor 服务管理器”窗口中：
   * **第 1 部分：** 点击 `Browse... (浏览...)` 并选择您的 Tor 文件夹 (`C:\tor\tor\`)。应用程序将自动检测 `torrc` 和 `tor.log` 路径。
   * 点击 **Save Paths to INI (将路径保存到 INI)**。
3. **第 2 部分（网桥）：** 如果您需要网桥：
   * 点击 **Fetch New Bridges (获取新网桥)**。应用程序将从 TorProject.org 获取 `obfs4` 网桥。
   * 点击 **Apply Paths and Bridges to torrc (将路径和网桥应用到 torrc)**。（将自动创建 `.bak` 备份文件）。
4. **第 3 部分（服务）：** 
   * 点击 **Install (安装)**。应用程序将请求管理员权限 (UAC) 以将 Tor 安装为 Windows 服务。
   * *注意：应用程序会自动授予 `SYSTEM` 对 Tor 文件夹的完全控制权限，以便服务能够写入日志。*

### 第 4 步：排查 Tor 服务故障
如果服务已安装但无法启动（Windows 错误 1064），通常是权限问题：
1. 在应用程序中点击 **Open services.msc (打开 services.msc)**。
2. 找到 `tor` 服务，右键点击 -> **属性**。
3. 转到 **登录** 选项卡。
4. 确保选中了 **本地系统帐户**。
5. 返回 WinProxyMon 并点击 **Start (启动)**。

---

## ⚙️ 配置文件 (`winproxymon.ini`)

应用程序会生成一个 INI 文件用于持久化存储。您可以通过界面或手动编辑它。

```ini
[settings]
interval_minutes = 1
ipv6 = false
disable_notifications_in_fullscreen = true
; 用于验证 HTTP 出口的网站列表。以逗号分隔。
check_urls = https://api.ipify.org, https://checkip.amazonaws.com, https://ident.me

[tor_settings]
torrc_path = C:\tor\tor\torrc
log_path = C:\tor\tor\tor.log
tor_exe_path = C:\tor\tor\tor.exe
service_name = tor

[proxy_1]
name = Tor Local
enabled = true
host = 127.0.0.1
port = 9050
protocol = socks5
username = 
password = 
plugin = tor
```

## 📂 项目结构

```
winproxymon/
├── img/                       # 托盘图标 (绿、黄、红)
├── plugins/                   # 插件目录
│   ├── tor_plugin.py          # Tor 界面与诊断逻辑
│   └── tor_plugin_scripts.py  # Windows 服务命令行工具 (UAC 提权)
├── winproxymon.py             # 主程序入口
├── winproxymon.spec           # PyInstaller 构建配置
└── README.md
```

## 📜 许可证

本项目基于 MIT 许可证开源 - 详见 [LICENSE](LICENSE) 文件。