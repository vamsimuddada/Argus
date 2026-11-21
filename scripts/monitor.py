#!/usr/bin/env python3
"""
ARGUS — 24/7 Host Health & Security Telemetry Daemon.
Continuously runs as a systemd service, monitoring system resources
and security logs, dispatching incidents to the ARGUS alert pipeline.
"""

import json
import logging
import os
import shutil
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────
ARGUS_API_URL = os.getenv("ARGUS_API_URL", "http://127.0.0.1:5000/alerts")
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))

# Thresholds
DISK_WARNING_PERCENT = float(os.getenv("DISK_WARNING_PERCENT", "15.0"))  # Set sensitive to capture active disk state
CPU_WARNING_PERCENT = float(os.getenv("CPU_WARNING_PERCENT", "85.0"))
MEM_WARNING_PERCENT = float(os.getenv("MEM_WARNING_PERCENT", "85.0"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("argus-monitor")

# Keep track of active alerts to prevent duplicate alert storms
_active_breaches = set()


def get_disk_usage() -> tuple[float, float, float]:
    """Return (used_percent, free_gb, total_gb)."""
    usage = shutil.disk_usage("/")
    total_gb = usage.total / (1024**3)
    free_gb = usage.free / (1024**3)
    used_percent = (usage.used / usage.total) * 100
    return used_percent, free_gb, total_gb


def get_memory_usage() -> float:
    """Return memory used percent from /proc/meminfo."""
    try:
        meminfo = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    meminfo[parts[0].strip()] = int(parts[1].split()[0])
        total = meminfo.get("MemTotal", 1)
        avail = meminfo.get("MemAvailable", total)
        return ((total - avail) / total) * 100
    except Exception:
        return 0.0


def get_cpu_load() -> float:
    """Return 1-minute load average normalized by core count."""
    try:
        load1, _, _ = os.getloadavg()
        cores = os.cpu_count() or 1
        return (load1 / cores) * 100
    except Exception:
        return 0.0


def check_ssh_failed_attempts() -> int:
    """Check systemd journal for recent failed SSH attempts."""
    try:
        result = subprocess.run(
            ["journalctl", "-u", "sshd", "--since", "5 minutes ago", "--no-pager"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.count("Failed password") + result.stdout.count("Invalid user")
    except Exception:
        return 0


def dispatch_alert(title: str, description: str, severity: str, breach_key: str):
    """Send an incident to the ARGUS alert pipeline."""
    if breach_key in _active_breaches:
        return  # Prevent alert spam while breach is active

    payload = {
        "title": title,
        "description": description,
        "severity": severity,
        "source": "systemd-monitor-daemon",
    }

    try:
        req = urllib.request.Request(
            ARGUS_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            alert_id = data.get("alert", {}).get("id")
            logger.info("🚨 Alert dispatched! ID: %s | %s", alert_id, title)
            _active_breaches.add(breach_key)
    except Exception as exc:
        logger.warning("Failed to dispatch alert to %s: %s", ARGUS_API_URL, exc)


def clear_breach_if_recovered(breach_key: str):
    if breach_key in _active_breaches:
        logger.info("✅ Metric normalized. Cleared breach state for: %s", breach_key)
        _active_breaches.remove(breach_key)


def run_checks():
    """Execute a single monitoring cycle."""
    # 1. Disk usage
    disk_pct, free_gb, total_gb = get_disk_usage()
    if disk_pct >= DISK_WARNING_PERCENT:
        dispatch_alert(
            title=f"Root Volume Capacity Threshold Exceeded ({disk_pct:.1f}%)",
            description=f"Storage pool '/' usage at {disk_pct:.1f}% ({free_gb:.1f} GB free of {total_gb:.1f} GB).",
            severity="high" if disk_pct >= 85 else "medium",
            breach_key="disk_usage",
        )
    else:
        clear_breach_if_recovered("disk_usage")

    # 2. Memory usage
    mem_pct = get_memory_usage()
    if mem_pct >= MEM_WARNING_PERCENT:
        dispatch_alert(
            title=f"System Memory Saturation Detected ({mem_pct:.1f}%)",
            description=f"Host available memory critically low. Consumption at {mem_pct:.1f}%.",
            severity="high",
            breach_key="memory_usage",
        )
    else:
        clear_breach_if_recovered("memory_usage")

    # 3. CPU Load
    cpu_pct = get_cpu_load()
    if cpu_pct >= CPU_WARNING_PERCENT:
        dispatch_alert(
            title=f"Host CPU Load Spike ({cpu_pct:.1f}%)",
            description=f"Average system load exceeded operational baseline: {cpu_pct:.1f}%.",
            severity="high",
            breach_key="cpu_usage",
        )
    else:
        clear_breach_if_recovered("cpu_usage")

    # 4. SSH Authentication Security
    failed_logins = check_ssh_failed_attempts()
    if failed_logins >= 3:
        dispatch_alert(
            title=f"SSH Brute Force Surge: {failed_logins} Failed Attempts",
            description=f"Automated authentication anomaly detected in sshd logs ({failed_logins} failures in 5m).",
            severity="critical",
            breach_key="ssh_bruteforce",
        )


def main():
    logger.info("🛡️ ARGUS Host Telemetry Monitor Daemon started. Polling every %ds...", POLL_INTERVAL_SECONDS)
    # Perform initial heartbeat/check
    try:
        run_checks()
    except Exception as exc:
        logger.error("Error during initial check: %s", exc)

    while True:
        try:
            time.sleep(POLL_INTERVAL_SECONDS)
            run_checks()
        except KeyboardInterrupt:
            logger.info("Shutting down monitor daemon.")
            break
        except Exception as exc:
            logger.error("Unexpected error in monitor loop: %s", exc)


if __name__ == "__main__":
    main()
