#!/usr/bin/env python3
"""
ARGUS — Incident Resolution CLI Helper.
Allows SOC operators and sysadmins to resolve alerts programmatically.
"""

import argparse
import json
import os
import sys
import urllib.request


def resolve_alert(alert_id: str, base_url: str):
    url = f"{base_url.rstrip('/')}/alerts/{alert_id}/resolve"
    try:
        req = urllib.request.Request(url, method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            print(f"✅ Alert '{alert_id}' marked as RESOLVED (at {data.get('resolved_at')})")
    except Exception as exc:
        print(f"❌ Failed to resolve alert '{alert_id}': {exc}", file=sys.stderr)


def list_open_alerts(base_url: str):
    url = f"{base_url.rstrip('/')}/alerts?status=open"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data.get("alerts", [])
    except Exception as exc:
        print(f"❌ Error fetching alerts: {exc}", file=sys.stderr)
        return []


def main():
    parser = argparse.ArgumentParser(description="Resolve ARGUS alerts via CLI")
    parser.add_argument("alert_id", nargs="?", help="ID of the alert to resolve")
    parser.add_argument("--all", action="store_true", help="Resolve all currently open alerts")
    parser.add_argument("--url", default="http://127.0.0.1:5000", help="Base URL of ARGUS API")
    args = parser.parse_args()

    if args.all:
        open_alerts = list_open_alerts(args.url)
        if not open_alerts:
            print("No open alerts found.")
            return
        for a in open_alerts:
            resolve_alert(a["id"], args.url)
    elif args.alert_id:
        resolve_alert(args.alert_id, args.url)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
