import os
import sys
import ctypes
import configparser
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QTextEdit,
    QGroupBox,
    QFormLayout,
    QMessageBox,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

sys.path.insert(0, os.path.dirname(__file__))
import tor_plugin_scripts as scripts


class TorSettingsDialog(QDialog):
    def __init__(self, ini_path):
        super().__init__()
        self.setWindowTitle("Tor Service Manager")
        self.setMinimumWidth(850)
        self.setMinimumHeight(450)
        self.ini_path = ini_path
        self.config = self.load_ini()
        self.current_status = "UNKNOWN"

        self.setup_ui()
        self.load_settings()
        self.restore_geometry()
        self.refresh_status()

    def load_ini(self):
        cfg = configparser.ConfigParser()
        cfg.read(self.ini_path)
        if not cfg.has_section("tor_settings"):
            cfg.add_section("tor_settings")
        return cfg

    def save_ini(self):
        with open(self.ini_path, "w") as f:
            self.config.write(f)

    def setup_ui(self):
        font = QFont()
        font.setPointSize(12)
        self.setFont(font)

        layout = QVBoxLayout()

        # 1. Пути установки
        path_box = QGroupBox("1. Tor Installation Paths")
        path_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        path_layout = QFormLayout()

        link = QLabel(
            '<a href="https://www.torproject.org/download/tor/">Download Tor Expert Bundle</a>'
        )
        link.setOpenExternalLinks(True)
        path_layout.addRow(link)

        self.txt_tor_dir = QLineEdit()
        self.txt_tor_dir.textChanged.connect(self.update_ui_state)
        btn_browse_dir = QPushButton("Browse...")
        btn_browse_dir.clicked.connect(self.browse_folder)
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.txt_tor_dir)
        dir_layout.addWidget(btn_browse_dir)
        path_layout.addRow("Tor Folder:", dir_layout)

        self.txt_torrc = QLineEdit()
        self.txt_torrc.textChanged.connect(self.update_ui_state)
        btn_browse_torrc = QPushButton("Browse...")
        btn_browse_torrc.clicked.connect(
            lambda: self.browse_file(self.txt_torrc, "Torrc files (torrc)")
        )
        torrc_layout = QHBoxLayout()
        torrc_layout.addWidget(self.txt_torrc)
        torrc_layout.addWidget(btn_browse_torrc)
        path_layout.addRow("torrc Path:", torrc_layout)

        self.txt_log = QLineEdit()
        self.txt_log.textChanged.connect(self.update_ui_state)
        btn_browse_log = QPushButton("Browse...")
        btn_browse_log.clicked.connect(
            lambda: self.browse_file(self.txt_log, "Log files (*.log)")
        )
        log_layout = QHBoxLayout()
        log_layout.addWidget(self.txt_log)
        log_layout.addWidget(btn_browse_log)
        path_layout.addRow("Log Path:", log_layout)

        self.btn_save_paths = QPushButton("Save Paths to INI")
        self.btn_save_paths.clicked.connect(self.save_paths)
        path_layout.addRow(self.btn_save_paths)

        path_box.setLayout(path_layout)
        layout.addWidget(path_box)

        # 2. Настройка мостов (Bridges)
        br_box = QGroupBox("2. Bridges Configuration")
        br_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        br_layout = QVBoxLayout()

        br_btn_layout = QHBoxLayout()
        self.btn_get_bridges = QPushButton("Fetch New Bridges")
        self.btn_get_bridges.clicked.connect(self.fetch_bridges)
        br_btn_layout.addWidget(self.btn_get_bridges)
        br_btn_layout.addStretch()
        br_layout.addLayout(br_btn_layout)

        self.txt_bridges = QTextEdit()
        self.txt_bridges.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.txt_bridges.setPlaceholderText("obfs4 IP:PORT FINGERPRINT cert=...")
        br_layout.addWidget(self.txt_bridges)

        br_box.setLayout(br_layout)
        layout.addWidget(br_box, 1)

        # 3. Сохранение в torrc
        save_box = QGroupBox("3. Save Configuration to torrc")
        save_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        save_layout = QVBoxLayout()
        self.btn_save_torrc = QPushButton("Apply Paths and Bridges to torrc")
        self.btn_save_torrc.clicked.connect(self.apply_torrc_config)
        save_layout.addWidget(self.btn_save_torrc)
        save_box.setLayout(save_layout)
        layout.addWidget(save_box)

        # 4. Управление сервисом (3 колонки)
        svc_box = QGroupBox("4. Windows Service Management")
        svc_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        svc_layout = QHBoxLayout()

        # Колонка 1: Подсказка, Установить, Удалить
        col1 = QVBoxLayout()
        svc_info = QLabel(
            "If service fails to start (Error 1064):\n"
            "1. Open services.msc -> find 'tor'\n"
            "2. Properties -> Log On -> Local System account\n"
            "3. Try to Start again."
        )
        svc_info.setWordWrap(True)
        svc_info.setStyleSheet("color: #555; font-size: 10pt;")
        col1.addWidget(svc_info)
        col1.addStretch()
        self.btn_install = QPushButton("Install")
        self.btn_remove = QPushButton("Remove")
        col1.addWidget(self.btn_install)
        col1.addWidget(self.btn_remove)

        # Колонка 2: Статус, Обновить, Старт, Стоп, Рестарт
        col2 = QVBoxLayout()
        self.lbl_status = QLabel("Status: CHECKING...")
        self.lbl_status.setStyleSheet(
            "font-size: 16pt; font-weight: bold; color: blue;"
        )
        self.lbl_status.setAlignment(Qt.AlignCenter)
        col2.addWidget(self.lbl_status)

        self.btn_status = QPushButton("Refresh Status")
        self.btn_start = QPushButton("Start")
        self.btn_stop = QPushButton("Stop")
        self.btn_restart = QPushButton("Restart")
        col2.addWidget(self.btn_status)
        col2.addWidget(self.btn_start)
        col2.addWidget(self.btn_stop)
        col2.addWidget(self.btn_restart)
        col2.addStretch()

        # Колонка 3: Открыть services.msc, tor.log, torrc
        col3 = QVBoxLayout()
        col3.addStretch()  # Выравнивание по центру
        self.btn_open_services = QPushButton("Open services.msc")
        self.btn_open_log = QPushButton("Open Tor Log")
        self.btn_open_torrc = QPushButton("Open torrc in Editor")
        col3.addWidget(self.btn_open_services)
        col3.addWidget(self.btn_open_log)
        col3.addWidget(self.btn_open_torrc)
        col3.addStretch()

        svc_layout.addLayout(col1, 2)
        svc_layout.addLayout(col2, 2)
        svc_layout.addLayout(col3, 2)
        svc_box.setLayout(svc_layout)
        layout.addWidget(svc_box)

        # Сигналы
        self.btn_install.clicked.connect(lambda: self.run_admin_action("install"))
        self.btn_remove.clicked.connect(lambda: self.run_admin_action("remove"))
        self.btn_start.clicked.connect(lambda: self.run_admin_action("start"))
        self.btn_stop.clicked.connect(lambda: self.run_admin_action("stop"))
        self.btn_restart.clicked.connect(lambda: self.run_admin_action("restart"))
        self.btn_status.clicked.connect(self.refresh_status)
        self.btn_open_services.clicked.connect(lambda: os.startfile("services.msc"))
        self.btn_open_log.clicked.connect(self.open_tor_log)
        self.btn_open_torrc.clicked.connect(self.open_torrc)

        self.setLayout(layout)
        self.update_ui_state()

    def browse_folder(self):
        start_dir = self.txt_tor_dir.text() or ""
        if not os.path.isdir(start_dir):
            start_dir = ""
        folder = QFileDialog.getExistingDirectory(self, "Select Tor Folder", start_dir)
        if folder:
            self.txt_tor_dir.setText(os.path.normpath(folder))
            torrc = os.path.join(folder, "torrc")
            log = os.path.join(folder, "tor.log")
            if os.path.exists(torrc) and not self.txt_torrc.text():
                self.txt_torrc.setText(os.path.normpath(torrc))
            if os.path.exists(log) and not self.txt_log.text():
                self.txt_log.setText(os.path.normpath(log))

    def browse_file(self, line_edit, filter_str):
        current_path = line_edit.text()
        start_dir = os.path.dirname(current_path) if current_path else ""
        if not os.path.isdir(start_dir):
            start_dir = ""
        file, _ = QFileDialog.getOpenFileName(
            self, "Select File", start_dir, filter_str
        )
        if file:
            line_edit.setText(os.path.normpath(file))

    def save_paths(self):
        tor_dir = os.path.normpath(self.txt_tor_dir.text().strip())
        tor_exe = os.path.join(tor_dir, "tor.exe") if tor_dir else ""
        tor_exe = os.path.normpath(tor_exe)

        if tor_dir and not os.path.exists(tor_exe):
            QMessageBox.warning(
                self, "Warning", "tor.exe not found in selected folder!"
            )
            return

        self.config["tor_settings"]["torrc_path"] = os.path.normpath(
            self.txt_torrc.text().strip()
        )
        self.config["tor_settings"]["log_path"] = os.path.normpath(
            self.txt_log.text().strip()
        )
        self.config["tor_settings"]["tor_exe_path"] = tor_exe
        self.config["tor_settings"]["service_name"] = "tor"
        self.save_ini()
        QMessageBox.information(self, "Saved", "Paths saved to INI.")

    def apply_torrc_config(self):
        torrc = os.path.normpath(self.txt_torrc.text().strip())
        if not torrc or not os.path.exists(torrc):
            QMessageBox.warning(self, "Error", "torrc path not configured.")
            return

        log_path = os.path.normpath(self.txt_log.text().strip())

        reply = QMessageBox.warning(
            self,
            "Confirm Overwrite",
            "This will OVERWRITE 'Log' and 'Bridge' lines in your torrc.\nA backup (.bak) will be created.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.No:
            return

        ok, msg = scripts.save_torrc(torrc, log_path, self.txt_bridges.toPlainText())
        if ok:
            QMessageBox.information(
                self,
                "Success",
                msg + "\nPlease restart the Tor service to apply changes.",
            )
        else:
            QMessageBox.critical(self, "Error", msg)

    def load_settings(self):
        s = self.config["tor_settings"]
        tor_exe = s.get("tor_exe_path", "")
        if tor_exe:
            self.txt_tor_dir.setText(os.path.normpath(os.path.dirname(tor_exe)))
        self.txt_torrc.setText(os.path.normpath(s.get("torrc_path", "")))
        self.txt_log.setText(os.path.normpath(s.get("log_path", "")))

        torrc = s.get("torrc_path", "")
        if torrc and os.path.exists(torrc):
            with open(torrc, "r", encoding="utf-8", errors="ignore") as f:
                bridges = [
                    line.strip()[7:] for line in f if line.strip().startswith("Bridge ")
                ]
                if bridges:
                    self.txt_bridges.setPlainText("\n".join(bridges))

    def restore_geometry(self):
        s = self.config["tor_settings"]
        w = s.getint("dialog_w", fallback=0)
        if w > 0:
            self.setGeometry(
                s.getint("dialog_x", fallback=100),
                s.getint("dialog_y", fallback=100),
                w,
                s.getint("dialog_h", fallback=450),
            )

    def closeEvent(self, event):
        geo = self.geometry()
        self.config["tor_settings"]["dialog_x"] = str(geo.x())
        self.config["tor_settings"]["dialog_y"] = str(geo.y())
        self.config["tor_settings"]["dialog_w"] = str(geo.width())
        self.config["tor_settings"]["dialog_h"] = str(geo.height())
        self.save_ini()
        event.accept()

    def refresh_status(self):
        ok, msg = scripts.get_service_status("tor")
        self.current_status = msg
        self.lbl_status.setText(f"Status: {msg}")

        if msg == "RUNNING":
            self.lbl_status.setStyleSheet(
                "font-size: 16pt; font-weight: bold; color: green;"
            )
        elif msg == "STOPPED":
            self.lbl_status.setStyleSheet(
                "font-size: 16pt; font-weight: bold; color: orange;"
            )
        else:
            self.lbl_status.setStyleSheet(
                "font-size: 16pt; font-weight: bold; color: blue;"
            )

        self.update_ui_state()

    def update_ui_state(self):
        # Проверка путей
        tor_dir = os.path.normpath(self.txt_tor_dir.text().strip())
        tor_exe = os.path.join(tor_dir, "tor.exe") if tor_dir else ""
        torrc = os.path.normpath(self.txt_torrc.text().strip())
        log_path = os.path.normpath(self.txt_log.text().strip())

        paths_filled = bool(tor_dir) and bool(torrc) and bool(log_path)
        torrc_exists = bool(torrc) and os.path.exists(torrc)
        log_exists = bool(log_path) and os.path.exists(log_path)
        tor_exe_exists = bool(tor_dir) and os.path.exists(tor_exe)

        # Кнопки путей
        self.btn_save_paths.setEnabled(paths_filled)
        self.btn_save_torrc.setEnabled(torrc_exists)
        self.btn_open_log.setEnabled(log_exists)
        self.btn_open_torrc.setEnabled(torrc_exists)

        # Кнопки сервисов
        is_running = self.current_status == "RUNNING"
        is_stopped = self.current_status == "STOPPED"
        is_pending = self.current_status in ["STARTING...", "STOPPING..."]
        is_installed = self.current_status not in ["NOT INSTALLED"]

        self.btn_install.setEnabled(
            not is_installed and tor_exe_exists and torrc_exists and not is_pending
        )
        self.btn_remove.setEnabled(is_stopped and not is_pending)
        self.btn_start.setEnabled(is_stopped and not is_pending)
        self.btn_stop.setEnabled(is_running and not is_pending)
        self.btn_restart.setEnabled(is_running and not is_pending)

    def run_admin_action(self, action):
        tor_dir = os.path.normpath(self.txt_tor_dir.text().strip())
        tor_exe = os.path.join(tor_dir, "tor.exe") if tor_dir else ""
        torrc = os.path.normpath(self.txt_torrc.text().strip())

        if action == "install" and not tor_exe:
            QMessageBox.warning(self, "Error", "Select Tor folder first!")
            return

        script_path = os.path.join(os.path.dirname(__file__), "tor_plugin_scripts.py")
        params = f'"{script_path}" {action}'
        if action == "install":
            params += f' --exe "{tor_exe}" --torrc "{torrc}"'

        self.lbl_status.setText("Status: EXECUTING...")
        self.lbl_status.setStyleSheet(
            "font-size: 16pt; font-weight: bold; color: blue;"
        )
        self.update_ui_state()

        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 0
        )

        # Увеличенное время ожидания для рестарта
        delay = 4000 if action == "restart" else 2500
        QTimer.singleShot(delay, self.read_admin_result)

    def read_admin_result(self):
        temp_file = os.path.join(os.environ.get("TEMP", "."), "tor_admin_result.txt")
        is_error = False
        msg_text = ""

        if os.path.exists(temp_file):
            with open(temp_file, "r", encoding="utf-8") as f:
                content = f.read()
            os.remove(temp_file)
            if "|" in content:
                status, msg_text = content.split("|", 1)
                if status == "ERROR":
                    is_error = True

        self.refresh_status()
        if is_error:
            QMessageBox.critical(self, "Action Failed", msg_text)

    def open_tor_log(self):
        log_path = os.path.normpath(self.txt_log.text().strip())
        if log_path and os.path.exists(log_path):
            os.startfile(log_path)
        else:
            QMessageBox.warning(
                self, "Log", "Log file not found. Check path in settings."
            )

    def open_torrc(self):
        torrc = os.path.normpath(self.txt_torrc.text().strip())
        if torrc and os.path.exists(torrc):
            os.startfile(torrc)
        else:
            QMessageBox.warning(
                self, "torrc", "torrc file not found. Check path in settings."
            )

    def fetch_bridges(self):
        from PyQt5.QtWidgets import QApplication

        QApplication.setOverrideCursor(Qt.WaitCursor)
        ok, msg = scripts.get_bridges()
        QApplication.restoreOverrideCursor()
        if ok:
            self.txt_bridges.setPlainText(msg)
        else:
            QMessageBox.critical(self, "Error", f"Failed to fetch bridges:\n{msg}")


def open_settings(ini_path):
    dialog = TorSettingsDialog(ini_path)
    dialog.exec_()


def diagnose_and_repair(config):
    import configparser

    tor_cfg = config.get("tor_settings", {})
    log_path = tor_cfg.get("log_path", "")

    if not log_path:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ini_path = os.path.join(base_dir, "winproxymon.ini")
        if os.path.exists(ini_path):
            cfg = configparser.ConfigParser()
            cfg.read(ini_path)
            if cfg.has_section("tor_settings"):
                log_path = cfg["tor_settings"].get("log_path", "")

    if not log_path or not os.path.exists(log_path):
        return f"Log not found: {log_path}"

    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()[-50:]
        errors = [
            l
            for l in lines
            if "warn" in l.lower() or "error" in l.lower() or "failed" in l.lower()
        ]
        if not errors:
            boot_lines = [l for l in lines if "Bootstrap" in l]
            if boot_lines:
                return boot_lines[-1].strip()
            return "No recent errors in log."
        return errors[-1].strip()
    except Exception as e:
        return f"Failed to read log: {e}"
