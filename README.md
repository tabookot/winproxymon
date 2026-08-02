[English](README.md) | [简体中文](README.zh.md) | [Русский](README.ru.md)

# 🛡️ WinProxyMon (Windows Proxy & Tor Monitor)

WinProxyMon is a lightweight, non-intrusive system tray application for Windows (7/8/10/11) designed to monitor proxy server availability. Built with Python and PyQt5, it provides real-time visual feedback, smart notifications, and a powerful built-in manager for Tor services.

Whether you are running a simple SOCKS5 proxy or a complex Tor bridge setup, WinProxyMon ensures you always know the exact state of your connection without leaving your desktop or getting interrupted during fullscreen gaming.

> *Authors' collective — GLM, GPT.*

## ✨ Key Features

* **Multi-Proxy Monitoring:** Monitor an unlimited number of proxies simultaneously (SOCKS4/5, HTTP, HTTPS).
* **Intelligent 3-Tier Diagnostics:** Doesn't just ping. It checks local internet, proxy port availability, and actual HTTP exit capability.
* **Smart Fullscreen Detection:** Automatically suppresses popup notifications when a fullscreen app (like a game or movie player) is running.
* **Visual Status Icons:** Instantly see if your proxy is ONLINE (Green), stuck/NO EXIT (Yellow), or OFFLINE (Red).
* **Built-in Tor Service Manager:** A dedicated graphical interface to install, start, stop, and restart the Tor Windows Service.
* **Bridge Fetcher & Applier:** Automatically fetches fresh `obfs4` bridges from TorProject.org and safely writes them to your `torrc` file.
* **Autostart Support:** Easily configure the app to launch with Windows.

---

## 🧠 How It Works (The Diagnostic Logic)

Unlike basic ping monitors, WinProxyMon uses a 3-tier check system to give you an accurate picture of your proxy's health:

1. **Local Internet Check:** Connects directly to `8.8.8.8:53`. If this fails, your PC has no local internet. Status: 🔴 **OFFLINE (NO LOCAL NET)**.
2. **TCP Port Check:** Tries to connect to the proxy's IP and Port. If it fails, the proxy software (e.g., Tor) is not running or crashed. Status: 🔴 **OFFLINE (PORT CLOSED)**.
3. **HTTP Exit Check:** Attempts to load a website through the proxy. If it fails but the port is open, the proxy is running but cannot route traffic (e.g., Tor bridges are dead). Status: 🟡 **NO EXIT**.
4. **Success:** If the HTTP request succeeds, the proxy is fully functional. Status: 🟢 **ONLINE**.

If a proxy is assigned a Plugin (like `tor`), the app will query the plugin for detailed error logs when a `NO EXIT` status occurs, displaying the exact Tor bootstrap failure reason in the tray tooltip and log.

---

## 🌐 Understanding `check_urls`

In your `winproxymon.ini` file, there is a setting called `check_urls`. This is a comma-separated list of websites the app uses to verify that traffic can successfully exit the proxy.

**How to choose good URLs for this list:**
1. **Plain Text Only:** The URL must return *nothing* except the IP address. If the site returns HTML, JSON, or extra words, the check will fail or pollute your logs. (e.g., `https://api.ipify.org` returns just `185.220.101.5`).
2. **Lightweight:** Use fast, minimal APIs. Avoid heavy web pages with lots of scripts.
3. **No Cloudflare/Tor Blocking:** Many standard websites block Tor exit nodes. The defaults provided are known to be Tor-friendly.
4. **Redundancy:** The app checks them in order. If the first URL is down, it tries the next. This prevents false "NO EXIT" alerts if a single check-IP site goes offline.

**Recommended defaults:**
```ini
check_urls = https://api.ipify.org, https://checkip.amazonaws.com, https://ident.me
```

---

## 🧅 What is the Tor Expert Bundle?

If you just want to browse the web anonymously, you use the **Tor Browser**. But if you want other applications (or your entire system) to route through Tor, you need the **Tor Expert Bundle**.

The Tor Expert Bundle is the pure Tor daemon without any graphical interface. It runs silently in the background as a process (or ideally, as a Windows Service) and exposes a SOCKS5 proxy (usually on `127.0.0.1:9050`). 

WinProxyMon is designed to manage this exact bundle. It can install the Tor daemon as a robust Windows Service, configure its bridges, read its logs, and monitor its SOCKS5 port.

---

## 🚀 Installation & Setup

### Run from Source (Python 3.8+)
1. Clone the repository:
   ```bash
   git clone https://github.com/tabookot/winproxymon.git
   cd winproxymon
   ```
2. Install dependencies:
   ```bash
   pip install PyQt5 requests PySocks
   ```
3. Run the application:
   ```bash
   python winproxymon.py
   ```

### Building an Executable (PyInstaller)
To compile your own `.exe`, ensure PyInstaller is installed, then use the provided `.spec` file to ensure all assets and plugins are bundled correctly:
```bash
pyinstaller winproxymon.spec
```
The compiled executable will be in the `dist/` folder.

---

## 🛠️ Complete Guide: Setting up Tor from Scratch

Follow these steps to set up the Tor Expert Bundle as a Windows Service managed by WinProxyMon.

### Step 1: Download Tor Expert Bundle
1. Go to the official Tor Project download page: [Tor Expert Bundle](https://www.torproject.org/download/tor/)
2. Download the Windows `.exe` installer or the `.zip` archive.
3. Extract it to a permanent folder, for example: `C:\tor\tor\` (Ensure `tor.exe` is inside this folder).

### Step 2: Configure WinProxyMon
1. Open WinProxyMon.
2. Right-click the tray icon and select **Manage Proxies...**
3. Click **Add** (or edit the default proxy).
4. Fill in the details:
   * **Name:** `Tor Local`
   * **Host:** `127.0.0.1` (or your LAN IP if Tor is on another PC)
   * **Port:** `9050` (Default Tor SOCKS5 port)
   * **Protocol:** `socks5`
   * **Plugin:** Select `tor` from the dropdown.
5. Click **Save**.

### Step 3: Configure Tor Service via Plugin UI
1. In the Manage Proxies window, click the **Configure Plugin...** button.
2. In the Tor Service Manager window:
   * **Section 1:** Click `Browse...` and select your Tor folder (`C:\tor\tor\`). The app will automatically detect `torrc` and `tor.log` paths.
   * Click **Save Paths to INI**.
3. **Section 2 (Bridges):** If you need bridges:
   * Click **Fetch New Bridges**. The app will fetch `obfs4` bridges from TorProject.org.
   * Click **Apply Paths and Bridges to torrc**. (A backup `.bak` file will be created automatically).
4. **Section 3 (Service):** 
   * Click **Install**. The app will request Admin rights (UAC) to install Tor as a Windows Service.
   * *Note: The app automatically grants `SYSTEM` full permissions to the Tor folder so the service can write logs.*

### Step 4: Troubleshooting Tor Service
If the service installs but fails to start (Windows Error 1064), it is usually a permissions issue:
1. Click **Open services.msc** in the app.
2. Find the `tor` service, right-click -> **Properties**.
3. Go to the **Log On** tab.
4. Ensure **Local System account** is selected.
5. Go back to WinProxyMon and click **Start**.

---

## ⚙️ Configuration File (`winproxymon.ini`)

The app generates an INI file for persistent storage. You can edit it manually or via the UI.

```ini
[settings]
interval_minutes = 1
ipv6 = false
disable_notifications_in_fullscreen = true
; List of websites to verify HTTP exit. Comma separated.
check_urls = https://api.ipify.org, https://checkip.amazonaws.com, https://ident.me

[tor_settings]
service_name = tor
torrc_path = C:\tor\tor\torrc
log_path = C:\tor\tor\tor.log
tor_exe_path = C:\tor\tor\tor.exe

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

## 📂 Project Structure

```
winproxymon/
├── img/                       # Tray icons (green, yellow, red)
├── plugins/                   # Plugin directory
│   ├── tor_plugin.py          # Tor UI and diagnostic logic
│   └── tor_plugin_scripts.py  # Windows Service CLI (UAC elevation)
├── winproxymon.py             # Main application entry point
├── winproxymon.spec           # PyInstaller build config
└── README.md
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.