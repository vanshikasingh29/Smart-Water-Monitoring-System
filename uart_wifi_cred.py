#!/usr/bin/env python3
"""
uart_wifi_config.py

Listen on UART for Wi-Fi credentials, then configure Wi-Fi on a Raspberry Pi.

Supported incoming UART message formats:
1) JSON:
   {"ssid":"MyWiFi","password":"MyPass123"}

2) Key/value:
   SSID=MyWiFi;PASSWORD=MyPass123

Run as root:
    sudo python3 uart_wifi_config.py

Requirements:
    pip install pyserial

Typical UART device:
    /dev/serial0
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time

WPA_SUPPLICANT_CONF = "/etc/wpa_supplicant/wpa_supplicant.conf"


def log(msg: str) -> None:
    print(f"[INFO] {msg}")


def err(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def run_cmd(cmd, check=True):
    result = subprocess.run(
        cmd,
        text=True,
        capture_output=True
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )
    return result


def escape_wpa_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')

def parse_message(raw: str):
    raw = raw.strip()
    if not raw:
        return None, None
    start=raw.find("WIFI:")
    if start == -1:
        return None, None

    payload = raw[start+5:]
    parts = payload.split("|", -1)
    if len (parts) !=2:
        return None, None

    ssid = parts[0].strip()
    password = parts[1].strip()

    if not ssid:
        return None, None

    return ssid, password

def use_networkmanager():
    return shutil.which("nmcli") is not None


def configure_with_nmcli(ssid: str, password: str) -> None:
    log("Using NetworkManager (nmcli) to configure Wi-Fi")

    # Ensure Wi-Fi radio is on
    run_cmd(["nmcli", "radio", "wifi", "on"])

    # Delete old connection with same name if it exists
    existing = run_cmd(["nmcli", "-t", "-f", "NAME", "connection", "show"], check=False)
    existing_names = existing.stdout.splitlines()

    if ssid in existing_names:
        log(f"Removing existing connection profile for SSID: {ssid}")
        run_cmd(["nmcli", "connection", "delete", ssid], check=False)

    # Create and connect
    if password:
        run_cmd(["nmcli", "dev", "wifi", "connect", ssid, "password", password])
    else:
        run_cmd(["nmcli", "dev", "wifi", "connect", ssid])

    log(f"Connected to Wi-Fi SSID: {ssid}")


def configure_with_wpa_supplicant(ssid: str, password: str) -> None:
    log("Using wpa_supplicant to configure Wi-Fi")

    if not os.path.exists(WPA_SUPPLICANT_CONF):
        raise FileNotFoundError(f"{WPA_SUPPLICANT_CONF} not found")

    with open(WPA_SUPPLICANT_CONF, "r", encoding="utf-8") as f:
        conf = f.read()

    escaped_ssid = escape_wpa_string(ssid)
    escaped_password = escape_wpa_string(password)

    network_block = (
        '\nnetwork={\n'
        f'    ssid="{escaped_ssid}"\n'
        f'    psk="{escaped_password}"\n'
        '    key_mgmt=WPA-PSK\n'
        '}\n'
    )

    if not password:
        network_block = (
            '\nnetwork={\n'
            f'    ssid="{escaped_ssid}"\n'
             '    key_mgmt=NONE\n'
            '}\n'
        )

    # Remove existing block for same SSID
    pattern = re.compile(
        r'network=\{\s*([^}]*?ssid="' + re.escape(escaped_ssid) + r'"[^}]*?)\s*\}',
        re.DOTALL
    )
    conf = re.sub(pattern, "", conf)

    conf = conf.rstrip() + "\n" + network_block

    backup_path = WPA_SUPPLICANT_CONF + ".bak"
    shutil.copy2(WPA_SUPPLICANT_CONF, backup_path)
    log(f"Backed up current config to {backup_path}")

    with open(WPA_SUPPLICANT_CONF, "w", encoding="utf-8") as f:
        f.write(conf)

    # Reconfigure Wi-Fi without reboot
    run_cmd(["wpa_cli", "-i", "wlan0", "reconfigure"], check=False)
    run_cmd(["systemctl", "restart", "dhcpcd"], check=False)

    log(f"Configured Wi-Fi SSID: {ssid}")

def main(line):
    try:
        ssid, password = parse_message(line)
        if not ssid:
            err("Could not parse SSID/password from message")
            return "ERROR:INVALID_FORMAT"
            ser.flush()


        try:
            if use_networkmanager():
                configure_with_nmcli(ssid, password)
            else:
                configure_with_wpa_supplicant(ssid, password)

            return "OK:WIFI_CONFIGURED"
            log("Wi-Fi configuration applied successfully")

        except Exception as config_error:
            err(str(config_error))
            return "ERROR:{str(config_error)}".encode("utf-8", errors="ignore")


    except Exception as e:
        err(f"Unexpected error: {e}")
        time.sleep(1)


