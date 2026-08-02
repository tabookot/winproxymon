import os
import sys
import time
import argparse
import subprocess
import requests
import shutil
import re


def run_hidden(cmd):
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)


def write_result(success, message):
    temp_file = os.path.join(os.environ.get("TEMP", "."), "tor_admin_result.txt")
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(f"{'SUCCESS' if success else 'ERROR'}|{message}")


def get_service_status(service_name="tor"):
    res = run_hidden(["sc", "query", service_name])
    if res.returncode == 0:
        if "RUNNING" in res.stdout:
            return True, "RUNNING"
        if "STOPPED" in res.stdout:
            return True, "STOPPED"
        if "START_PENDING" in res.stdout:
            return True, "STARTING..."
        if "STOP_PENDING" in res.stdout:
            return True, "STOPPING..."
        if "PAUSED" in res.stdout:
            return True, "PAUSED"
        return True, "UNKNOWN"
    return False, "NOT INSTALLED"


def install_service(tor_exe, torrc, service_name="tor"):
    try:
        run_hidden([tor_exe, "--service", "remove"])
    except:
        pass

    res = run_hidden([tor_exe, "--service", "install", "-options", "-f", torrc])
    if res.returncode != 0:
        return False, res.stderr or res.stdout or "Install failed"

    run_hidden(["sc", "config", service_name, "start=", "auto"])
    tor_dir = os.path.dirname(tor_exe)
    run_hidden(["icacls", tor_dir, "/grant", "SYSTEM:(OI)(CI)F", "/T"])
    return True, "Service installed. Auto-start enabled. SYSTEM permissions set."


def remove_service(tor_exe=None, service_name="tor"):
    cmd = (
        [tor_exe, "--service", "remove"] if tor_exe else ["sc", "delete", service_name]
    )
    res = run_hidden(cmd)
    return res.returncode == 0, "Service removed."


def start_service(service_name="tor"):
    res = run_hidden(["sc", "start", service_name])
    if res.returncode != 0:
        return False, f"Failed to start. Exit code: {res.returncode}"
    return True, "Service start command sent."


def stop_service(service_name="tor"):
    res = run_hidden(["sc", "stop", service_name])
    if res.returncode != 0:
        return False, f"Failed to stop. Exit code: {res.returncode}"
    return True, "Service stop command sent."


def restart_service(service_name="tor"):
    run_hidden(["sc", "stop", service_name])
    time.sleep(3)  # Ждем 3 секунды для надежной остановки
    res = run_hidden(["sc", "start", service_name])
    if res.returncode != 0:
        return False, f"Failed to restart. Exit code: {res.returncode}"
    return True, "Service restart command sent."


def get_bridges():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(
            "https://bridges.torproject.org/bridges?transport=obfs4",
            headers=headers,
            timeout=10,
        )
        if r.ok:
            clean_text = re.sub(r"<[^>]+>", "", r.text)
            lines = clean_text.splitlines()
            bridges = [l.strip() for l in lines if l.strip().startswith("obfs4")]
            if bridges:
                return True, "\n".join(bridges)
            return False, "No obfs4 bridges found on page."
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)


def save_torrc(torrc_path, log_path, bridges_text):
    if not os.path.exists(torrc_path):
        return False, "torrc not found"

    shutil.copy2(torrc_path, torrc_path + ".bak")

    with open(torrc_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    content = re.sub(
        r"(?m)^(UseBridges|Bridge|Log notice file)[^\r\n]*\r?\n", "", content
    )

    if content and not content.endswith("\n"):
        content += "\n"

    log_path_fwd = log_path.replace("\\", "/")

    config_lines = []
    if log_path_fwd:
        config_lines.append(f"Log notice file {log_path_fwd}")

    if bridges_text.strip():
        config_lines.append("UseBridges 1")
        for b in bridges_text.splitlines():
            b = b.strip()
            if b:
                config_lines.append(f"Bridge {b}")
    else:
        config_lines.append("UseBridges 0")

    content += "\n".join(config_lines) + "\n"

    with open(torrc_path, "w", encoding="utf-8") as f:
        f.write(content)

    return True, "Configuration saved to torrc. Backup created (.bak)."


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=["install", "remove", "start", "stop", "restart", "status"]
    )
    parser.add_argument("--exe")
    parser.add_argument("--torrc")
    parser.add_argument("--service", default="tor")
    args = parser.parse_args()

    if args.action == "status":
        ok, msg = get_service_status(args.service)
        write_result(ok, msg)
    elif args.action == "install":
        ok, msg = install_service(args.exe, args.torrc, args.service)
        write_result(ok, msg)
    elif args.action == "remove":
        ok, msg = remove_service(args.exe, args.service)
        write_result(ok, msg)
    elif args.action == "start":
        ok, msg = start_service(args.service)
        write_result(ok, msg)
    elif args.action == "stop":
        ok, msg = stop_service(args.service)
        write_result(ok, msg)
    elif args.action == "restart":
        ok, msg = restart_service(args.service)
        write_result(ok, msg)
