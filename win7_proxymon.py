import os
import sys
import socket
import logging
import configparser
import ctypes
import winreg
from ctypes import wintypes

import requests
from PyQt5.QtWidgets import (
    QApplication,
    QSystemTrayIcon,
    QMenu,
    QAction,
    QMessageBox,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QComboBox,
    QCheckBox,
    QWidget,
)
from PyQt5.QtGui import QIcon, QFont  # <-- Добавлен QFont
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, QSharedMemory, Qt

# ==========================================
# 1. Constants & Globals
# ==========================================
APP_NAME = "win7_proxymon"

BASE = getattr(sys, "_MEIPASS", os.path.abspath("."))
EXEC_DIR = os.path.dirname(
    sys.executable if getattr(sys, "frozen", False) else __file__
)
INI_PATH = os.path.join(EXEC_DIR, f"{APP_NAME}.ini")
LOG_PATH = os.path.join(EXEC_DIR, f"{APP_NAME}.log")
IMG_DIR = os.path.join(BASE, "img")

logging.basicConfig(
    filename=LOG_PATH, level=logging.INFO, format="[%(asctime)s] %(message)s"
)

# ==========================================
# 2. Windows API for fullscreen detection
# ==========================================
user32 = ctypes.windll.user32
SM_CXSCREEN = 0
SM_CYSCREEN = 1


class WINDOWINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcWindow", wintypes.RECT),
        ("rcClient", wintypes.RECT),
        ("dwStyle", wintypes.DWORD),
        ("dwExStyle", wintypes.DWORD),
        ("dwWindowStatus", wintypes.DWORD),
        ("cxWindowBorders", wintypes.UINT),
        ("cyWindowBorders", wintypes.UINT),
        ("atomWindowType", wintypes.ATOM),
        ("wCreatorVersion", wintypes.WORD),
    ]


def is_fullscreen_app_running():
    try:
        sw = user32.GetSystemMetrics(SM_CXSCREEN)
        sh = user32.GetSystemMetrics(SM_CYSCREEN)
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False

        wi = WINDOWINFO()
        wi.cbSize = ctypes.sizeof(WINDOWINFO)
        if not user32.GetWindowInfo(hwnd, ctypes.byref(wi)):
            return False

        wr = wi.rcWindow
        is_fs_size = wr.right - wr.left == sw and wr.bottom - wr.top == sh
        is_at_origin = wr.left == 0 and wr.top == 0

        if hwnd == user32.GetDesktopWindow() or hwnd == user32.GetShellWindow():
            return False

        return is_fs_size and is_at_origin
    except Exception as e:
        logging.error(f"Fullscreen check error: {e}")
        return False


# ==========================================
# 3. Configuration & Autostart
# ==========================================
def load_config():
    cfg = configparser.ConfigParser()
    cfg.read(INI_PATH)

    if not cfg.has_section("settings"):
        cfg.add_section("settings")

    s = cfg["settings"]

    proxies = []
    for section in cfg.sections():
        if section.startswith("proxy_"):
            p = cfg[section]
            proxies.append(
                {
                    "id": section,
                    "name": p.get("name", section),
                    "enabled": p.getboolean("enabled", fallback=True),
                    "host": p.get("host", "127.0.0.1"),
                    "port": p.get("port", "1080"),
                    "protocol": p.get("protocol", "socks5"),
                    "username": p.get("username", ""),
                    "password": p.get("password", ""),
                }
            )

    if not proxies:
        proxies.append(
            {
                "id": "proxy_1",
                "name": "Default",
                "enabled": True,
                "host": "127.0.0.1",
                "port": "1080",
                "protocol": "socks5",
                "username": "",
                "password": "",
            }
        )

    ui_geo = {
        "x": s.getint("dialog_x", fallback=100),
        "y": s.getint("dialog_y", fallback=100),
        "w": s.getint("dialog_w", fallback=750),
        "h": s.getint("dialog_h", fallback=400),
    }

    return {
        "proxies": proxies,
        "interval_ms": int(s.get("interval_minutes", 1)) * 60000,
        "ipv6": s.getboolean("ipv6", fallback=False),
        "disable_notifications_in_fullscreen": s.getboolean(
            "disable_notifications_in_fullscreen", fallback=True
        ),
        "ui_geometry": ui_geo,
    }


def save_config_settings(config_dict):
    cfg = configparser.ConfigParser()
    cfg.read(INI_PATH)

    for section in list(cfg.sections()):
        if section.startswith("proxy_"):
            cfg.remove_section(section)

    geo = config_dict.get("ui_geometry", {})

    cfg["settings"] = {
        "interval_minutes": str(int(config_dict.get("interval_ms", 60000)) // 60000),
        "ipv6": str(config_dict.get("ipv6", False)).lower(),
        "disable_notifications_in_fullscreen": str(
            config_dict.get("disable_notifications_in_fullscreen", True)
        ).lower(),
        "dialog_x": str(geo.get("x", 100)),
        "dialog_y": str(geo.get("y", 100)),
        "dialog_w": str(geo.get("w", 750)),
        "dialog_h": str(geo.get("h", 400)),
    }

    for p in config_dict.get("proxies", []):
        cfg[p["id"]] = {
            "name": p.get("name", p["id"]),
            "enabled": str(p.get("enabled", True)).lower(),
            "host": p.get("host", ""),
            "port": str(p.get("port", "")),
            "protocol": p.get("protocol", "socks5"),
            "username": p.get("username", ""),
            "password": p.get("password", ""),
        }

    with open(INI_PATH, "w") as f:
        cfg.write(f)


def is_autostart_enabled():
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\\Microsoft\\Windows\\CurrentVersion\\Run",
            0,
            winreg.KEY_READ,
        ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def enable_autostart():
    exe_path = os.path.join(EXEC_DIR, os.path.basename(sys.executable))
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\\Microsoft\\Windows\\CurrentVersion\\Run",
        0,
        winreg.KEY_WRITE,
    ) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)


def disable_autostart():
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\\Microsoft\\Windows\\CurrentVersion\\Run",
            0,
            winreg.KEY_WRITE,
        ) as key:
            winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass


# ==========================================
# 4. Network Checks
# ==========================================
def check_local_internet():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except:
        return False


def is_port_open(host, port):
    try:
        with socket.create_connection((host, int(port)), timeout=2):
            return True
    except:
        return False


def check_proxy(proxy_cfg, use_ipv6):
    try:
        session = requests.Session()
        session.trust_env = False

        auth = ""
        if proxy_cfg["username"] and proxy_cfg["password"]:
            auth = f"{proxy_cfg['username']}:{proxy_cfg['password']}@"

        proxy_url = (
            f"{proxy_cfg['protocol']}://{auth}{proxy_cfg['host']}:{proxy_cfg['port']}"
        )
        session.proxies = {"http": proxy_url, "https": proxy_url}

        original_getaddrinfo = socket.getaddrinfo
        if not use_ipv6:

            def v4_only_getaddrinfo(*args, **kwargs):
                return [
                    ai
                    for ai in original_getaddrinfo(*args, **kwargs)
                    if ai[0] == socket.AF_INET
                ]

            socket.getaddrinfo = v4_only_getaddrinfo

        try:
            r = session.get("https://ifconfig.me", timeout=7)
            if r.ok:
                return True, "OK"
            else:
                return False, f"HTTP Error {r.status_code}"
        finally:
            socket.getaddrinfo = original_getaddrinfo

    except requests.exceptions.ProxyError as e:
        if "407" in str(e):
            return False, "Auth failed (407)"
        return False, "Connection refused"
    except requests.exceptions.ConnectTimeout:
        return False, "Connection timeout"
    except requests.exceptions.ReadTimeout:
        return False, "Read timeout (no exit)"
    except Exception as e:
        return False, str(e)


# ==========================================
# 5. Threaded Worker
# ==========================================
class ProxyCheckThread(QThread):
    finished = pyqtSignal(list, str, bool)

    def __init__(self, config, manual=False):
        super().__init__()
        self.config = config
        self.manual = manual

    def run(self):
        enabled_proxies = [p for p in self.config["proxies"] if p["enabled"]]
        results = []

        if not enabled_proxies:
            self.finished.emit(
                results, "[MANUAL]" if self.manual else "[AUTO]", self.manual
            )
            return

        local_net_ok = check_local_internet()

        for p in enabled_proxies:
            proxy_ok, detail = check_proxy(p, self.config.get("ipv6", False))

            if proxy_ok:
                icon = "icon_green.png"
                status = "ONLINE"
            else:
                if not local_net_ok:
                    icon = "icon_red.png"
                    status = "NO LOCAL NET"
                else:
                    port_ok = is_port_open(p["host"], p["port"])
                    if not port_ok:
                        icon = "icon_red.png"
                        status = "OFFLINE"
                    else:
                        icon = "icon_yellow.png"
                        status = "NO EXIT"

            results.append(
                {"name": p["name"], "status": status, "detail": detail, "icon": icon}
            )

        tag = "[MANUAL]" if self.manual else "[AUTO]"
        self.finished.emit(results, tag, self.manual)


# ==========================================
# 6. UI Dialog (Master-Detail) с крупным шрифтом
# ==========================================
class ProxyManagerDialog(QDialog):
    def __init__(self, current_proxies, geometry=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Proxies")
        self.proxies = [p.copy() for p in current_proxies]
        self.current_index = -1

        self.setup_ui()

        if geometry:
            self.setGeometry(geometry["x"], geometry["y"], geometry["w"], geometry["h"])
        else:
            self.resize(750, 400)

        self.load_list()
        if self.proxies:
            self.list_widget.setCurrentRow(0)

    def setup_ui(self):
        # --- УВЕЛИЧЕНИЕ ШРИФТА В 1.5 РАЗА ---
        font = QFont()
        font.setPointSize(12)  # Стандарт ~8pt. 12pt это увеличение в 1.5 раза
        self.setFont(font)
        # ------------------------------------

        layout = QVBoxLayout()

        splitter = QSplitter(Qt.Horizontal)

        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.on_item_changed)
        splitter.addWidget(self.list_widget)

        detail_widget = QWidget()
        form_layout = QFormLayout(detail_widget)
        form_layout.setContentsMargins(10, 10, 10, 10)

        self.chk_enabled = QCheckBox("Enabled")
        self.txt_name = QLineEdit()
        self.txt_host = QLineEdit()
        self.txt_port = QLineEdit()
        self.cmb_protocol = QComboBox()
        self.cmb_protocol.addItems(["socks5", "http", "https", "socks4"])
        self.txt_username = QLineEdit()
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)

        form_layout.addRow(self.chk_enabled)
        form_layout.addRow("Name:", self.txt_name)
        form_layout.addRow("Host:", self.txt_host)
        form_layout.addRow("Port:", self.txt_port)
        form_layout.addRow("Protocol:", self.cmb_protocol)
        form_layout.addRow("Username:", self.txt_username)
        form_layout.addRow("Password:", self.txt_password)

        splitter.addWidget(detail_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add")
        self.btn_remove = QPushButton("Remove")
        self.btn_save = QPushButton("Save")
        self.btn_cancel = QPushButton("Cancel")

        self.btn_add.clicked.connect(self.add_proxy)
        self.btn_remove.clicked.connect(self.remove_proxy)
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_remove)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def load_list(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for p in self.proxies:
            self.list_widget.addItem(p.get("name", "Unnamed"))
        self.list_widget.blockSignals(False)

    def on_item_changed(self, row):
        if self.current_index != -1 and self.current_index < len(self.proxies):
            self.save_fields_to_proxy(self.current_index)

        self.current_index = row

        if row == -1 or row >= len(self.proxies):
            self.clear_detail_fields()
            return

        p = self.proxies[row]
        self.chk_enabled.setChecked(p["enabled"])
        self.txt_name.setText(p["name"])
        self.txt_host.setText(p["host"])
        self.txt_port.setText(p["port"])
        self.cmb_protocol.setCurrentText(p["protocol"])
        self.txt_username.setText(p["username"])
        self.txt_password.setText(p["password"])

    def save_fields_to_proxy(self, index):
        if index == -1 or index >= len(self.proxies):
            return
        p = self.proxies[index]
        p["enabled"] = self.chk_enabled.isChecked()
        p["name"] = self.txt_name.text()
        p["host"] = self.txt_host.text()
        p["port"] = self.txt_port.text()
        p["protocol"] = self.cmb_protocol.currentText()
        p["username"] = self.txt_username.text()
        p["password"] = self.txt_password.text()

        item = self.list_widget.item(index)
        if item:
            item.setText(p["name"])

    def clear_detail_fields(self):
        self.chk_enabled.setChecked(False)
        self.txt_name.clear()
        self.txt_host.clear()
        self.txt_port.clear()
        self.cmb_protocol.setCurrentIndex(0)
        self.txt_username.clear()
        self.txt_password.clear()

    def add_proxy(self):
        if self.current_index != -1:
            self.save_fields_to_proxy(self.current_index)

        new_proxy = {
            "id": f"proxy_{len(self.proxies)+1}_{os.urandom(2).hex()}",
            "enabled": True,
            "name": f"Proxy {len(self.proxies)+1}",
            "host": "127.0.0.1",
            "port": "1080",
            "protocol": "socks5",
            "username": "",
            "password": "",
        }
        self.proxies.append(new_proxy)
        self.load_list()
        self.list_widget.setCurrentRow(len(self.proxies) - 1)

    def remove_proxy(self):
        if self.current_index == -1:
            return
        del self.proxies[self.current_index]
        self.current_index = -1
        self.load_list()
        if self.proxies:
            self.list_widget.setCurrentRow(0)

    def get_proxies(self):
        if self.current_index != -1 and self.current_index < len(self.proxies):
            self.save_fields_to_proxy(self.current_index)
        return self.proxies

    def get_geometry(self):
        geo = self.geometry()
        return {"x": geo.x(), "y": geo.y(), "w": geo.width(), "h": geo.height()}


# ==========================================
# 7. Main Tray Application Class
# ==========================================
class TrayApp:
    def __init__(self, app):
        self.app = app
        self.config = load_config()
        self.threads = []
        self.last_global_status = None
        self.timer = QTimer()

        self.init_tray()
        self.rebuild_menu()

        self.update_status()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(self.config["interval_ms"])

    def get_icon_path(self, icon_name):
        path = os.path.join(IMG_DIR, icon_name)
        if os.path.exists(path):
            return path
        return os.path.join(BASE, icon_name)

    def init_tray(self):
        self.tray = QSystemTrayIcon(QIcon(self.get_icon_path("icon_red.png")), self.app)
        self.tray.setToolTip(APP_NAME)
        self.tray.setVisible(True)
        self.tray.activated.connect(self.handle_tray_activated)
        self.menu = QMenu()

    def rebuild_menu(self):
        self.menu.clear()

        self.manage_action = QAction("Manage Proxies...", self.menu)
        self.manage_action.triggered.connect(self.open_proxy_manager)
        self.menu.addAction(self.manage_action)

        self.monitor_menu = self.menu.addMenu("Monitor")
        if not self.config["proxies"]:
            empty_act = QAction("No proxies configured", self.monitor_menu)
            empty_act.setEnabled(False)
            self.monitor_menu.addAction(empty_act)
        else:
            for p in self.config["proxies"]:
                act = QAction(p["name"], self.monitor_menu, checkable=True)
                act.setChecked(p["enabled"])
                act.triggered.connect(
                    lambda checked, pid=p["id"]: self.toggle_proxy_monitoring(
                        pid, checked
                    )
                )
                self.monitor_menu.addAction(act)

        self.menu.addSeparator()

        self.log_action = QAction("Open Log", self.menu)
        self.log_action.triggered.connect(self.open_log)
        self.menu.addAction(self.log_action)

        self.menu.addSeparator()

        self.autostart_action = QAction("Autostart", self.menu, checkable=True)
        self.autostart_action.setChecked(is_autostart_enabled())
        self.autostart_action.triggered.connect(self.toggle_autostart)
        self.menu.addAction(self.autostart_action)

        self.fs_action = QAction("Block Fullscreen Notifs", self.menu, checkable=True)
        self.fs_action.setChecked(
            self.config.get("disable_notifications_in_fullscreen", True)
        )
        self.fs_action.triggered.connect(self.toggle_fullscreen_notifications)
        self.menu.addAction(self.fs_action)

        self.menu.addSeparator()

        self.exit_action = QAction("Exit", self.menu)
        self.exit_action.triggered.connect(self.app.quit)
        self.menu.addAction(self.exit_action)

        self.tray.setContextMenu(self.menu)

    def handle_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.update_status(manual=True)

    def update_status(self, manual=False):
        thread = ProxyCheckThread(self.config, manual)
        self.threads.append(thread)
        thread.finished.connect(self.on_check_finished)
        thread.finished.connect(lambda *_: self.threads.remove(thread))
        thread.start()

    def on_check_finished(self, results, tag, manual_override):
        if not results:
            icon_name = "icon_red.png"
            status = "DISABLED"
            msg = "No proxies enabled for monitoring"
            tooltip = f"{APP_NAME} (Disabled)"
        else:
            icons_list = [r["icon"] for r in results]
            if "icon_red.png" in icons_list:
                icon_name = "icon_red.png"
            elif "icon_yellow.png" in icons_list:
                icon_name = "icon_yellow.png"
            else:
                icon_name = "icon_green.png"

            msg_parts = []
            tooltip_parts = []
            for r in results:
                msg_parts.append(f"{r['name']}: {r['status']} ({r['detail']})")
                tooltip_parts.append(f"{r['name']}: {r['status']}")

            msg = "\n".join(msg_parts)
            tooltip = f"{APP_NAME}\n" + "\n".join(tooltip_parts)
            status = icon_name.split("_")[1].split(".")[0].upper()

        self.tray.setIcon(QIcon(self.get_icon_path(icon_name)))
        self.tray.setToolTip(tooltip)

        should_show_notification = manual_override or self.last_global_status != status

        if should_show_notification:
            if (
                self.config.get("disable_notifications_in_fullscreen", True)
                and is_fullscreen_app_running()
            ):
                logging.info(f"{tag} [{status}] Notifications suppressed (fullscreen)")
            else:
                self.tray.showMessage(
                    "Proxy Status", msg, QSystemTrayIcon.Information, 5000
                )
                logging.info(f"{tag} [{status}] {msg} [NOTIF: SHOWN]")
        else:
            logging.info(f"{tag} [{status}] {msg} [NOTIF: SKIP - no change]")

        self.last_global_status = status

        self.timer.stop()
        self.timer.start(self.config["interval_ms"])

    def open_proxy_manager(self):
        dialog = ProxyManagerDialog(
            self.config["proxies"], self.config.get("ui_geometry")
        )

        self.config["ui_geometry"] = dialog.get_geometry()

        if dialog.exec_():
            self.config["proxies"] = dialog.get_proxies()

        save_config_settings(self.config)

        self.config = load_config()
        self.rebuild_menu()
        self.update_status(manual=True)

    def toggle_proxy_monitoring(self, proxy_id, state):
        cfg = configparser.ConfigParser()
        cfg.read(INI_PATH)
        if proxy_id in cfg:
            cfg[proxy_id]["enabled"] = str(state).lower()
            with open(INI_PATH, "w") as f:
                cfg.write(f)

        self.config = load_config()
        self.rebuild_menu()

    def toggle_fullscreen_notifications(self):
        self.config["disable_notifications_in_fullscreen"] = not self.config.get(
            "disable_notifications_in_fullscreen", True
        )
        save_config_settings(self.config)
        self.rebuild_menu()

    def toggle_autostart(self):
        if self.autostart_action.isChecked():
            enable_autostart()
            self.tray.showMessage(
                "Autostart", "Added to startup", QSystemTrayIcon.Information, 3000
            )
            logging.info("[SETTINGS] Autostart: enabled")
        else:
            disable_autostart()
            self.tray.showMessage(
                "Autostart", "Removed from startup", QSystemTrayIcon.Information, 3000
            )
            logging.info("[SETTINGS] Autostart: disabled")

    def open_log(self):
        if os.path.exists(LOG_PATH):
            os.startfile(LOG_PATH)
        else:
            self.tray.showMessage(
                "Log", "Log file not found.", QSystemTrayIcon.Warning, 3000
            )


# ==========================================
# 8. Entry Point
# ==========================================
if __name__ == "__main__":
    APP_UNIQUE_KEY = f"{APP_NAME}_unique_key_v1"
    shared_memory = QSharedMemory(APP_UNIQUE_KEY)

    if not shared_memory.create(1):
        app = QApplication(sys.argv)
        QMessageBox.warning(None, APP_NAME, "Application already running!")
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    main_app = TrayApp(app)
    sys.exit(app.exec_())
