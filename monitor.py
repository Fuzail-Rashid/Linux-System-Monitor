#!/usr/bin/env python3
"""
System Monitor with Email Alerts
Checks CPU, RAM, and Disk usage and sends an email alert when any threshold is crossed.

Usage:
    python3 monitor.py              # run once
    python3 monitor.py --loop       # run every N seconds (set INTERVAL below)

Cron example (every 5 minutes):
    */5 * * * * /usr/bin/python3 /opt/system-monitor/monitor.py >> /var/log/system-monitor.log 2>&1
"""

import os
import smtplib
import argparse
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import psutil

# ── Thresholds ────────────────────────────────────────────────────────────────
CPU_THRESHOLD  = 80   # percent
RAM_THRESHOLD  = 85   # percent
DISK_THRESHOLD = 90   # percent

# ── Email config (set via environment variables) ──────────────────────────────
SMTP_HOST     = os.getenv("SMTP_HOST",     "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER",     "")       # your Gmail address
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")       # Gmail app password
EMAIL_FROM    = os.getenv("EMAIL_FROM",    SMTP_USER)
EMAIL_TO      = os.getenv("EMAIL_TO",      "")       # recipient address

# ── Loop interval (used with --loop) ─────────────────────────────────────────
INTERVAL = 60  # seconds


# =============================================================================
#  METRIC COLLECTION
# =============================================================================

def get_metrics():
    """Collect current CPU, RAM, and per-disk usage."""
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent

    disks = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                "mountpoint": part.mountpoint,
                "percent":    usage.percent,
                "used_gb":    round(usage.used  / 1024**3, 1),
                "total_gb":   round(usage.total / 1024**3, 1),
            })
        except PermissionError:
            pass

    return {"cpu": cpu, "ram": ram, "disks": disks}


def check_thresholds(metrics):
    """Return a list of triggered alerts."""
    alerts = []

    if metrics["cpu"] >= CPU_THRESHOLD:
        alerts.append({
            "type":    "CPU",
            "value":   f"{metrics['cpu']}%",
            "threshold": f"{CPU_THRESHOLD}%",
            "message": f"CPU usage is at {metrics['cpu']}%, which exceeds the {CPU_THRESHOLD}% threshold.",
        })

    if metrics["ram"] >= RAM_THRESHOLD:
        alerts.append({
            "type":    "RAM",
            "value":   f"{metrics['ram']}%",
            "threshold": f"{RAM_THRESHOLD}%",
            "message": f"RAM usage is at {metrics['ram']}%, which exceeds the {RAM_THRESHOLD}% threshold.",
        })

    for disk in metrics["disks"]:
        if disk["percent"] >= DISK_THRESHOLD:
            alerts.append({
                "type":    f"Disk ({disk['mountpoint']})",
                "value":   f"{disk['percent']}%",
                "threshold": f"{DISK_THRESHOLD}%",
                "message": (
                    f"Disk usage on {disk['mountpoint']} is at {disk['percent']}% "
                    f"({disk['used_gb']} GB / {disk['total_gb']} GB), "
                    f"exceeding the {DISK_THRESHOLD}% threshold."
                ),
            })

    return alerts


# =============================================================================
#  EMAIL
# =============================================================================

def build_email_body(alerts, metrics):
    """Build a plain-text + HTML email body."""
    hostname  = os.uname().nodename
    now       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count     = len(alerts)

    # ── Plain text ────────────────────────────────────────────────────────────
    lines = [
        f"System Alert — {hostname}",
        f"Time: {now}",
        f"{count} threshold(s) exceeded\n",
    ]
    for a in alerts:
        lines.append(f"  [{a['type']}]  {a['value']} (limit: {a['threshold']})")
        lines.append(f"  {a['message']}\n")
    lines += [
        "── Current Metrics ──────────────────",
        f"  CPU  : {metrics['cpu']}%",
        f"  RAM  : {metrics['ram']}%",
    ]
    for d in metrics["disks"]:
        lines.append(f"  Disk {d['mountpoint']} : {d['percent']}%")
    text_body = "\n".join(lines)

    # ── HTML ──────────────────────────────────────────────────────────────────
    alert_rows = ""
    for a in alerts:
        alert_rows += f"""
        <tr>
          <td style="padding:10px 14px;font-weight:600;color:#f43f5e">{a['type']}</td>
          <td style="padding:10px 14px;font-family:monospace;color:#f43f5e">{a['value']}</td>
          <td style="padding:10px 14px;color:#94a3b8">limit: {a['threshold']}</td>
          <td style="padding:10px 14px;color:#cbd5e1">{a['message']}</td>
        </tr>"""

    metric_rows = f"""
        <tr><td style="padding:8px 14px;color:#94a3b8">CPU</td>
            <td style="padding:8px 14px;font-family:monospace">{metrics['cpu']}%</td></tr>
        <tr><td style="padding:8px 14px;color:#94a3b8">RAM</td>
            <td style="padding:8px 14px;font-family:monospace">{metrics['ram']}%</td></tr>"""
    for d in metrics["disks"]:
        metric_rows += f"""
        <tr><td style="padding:8px 14px;color:#94a3b8">Disk {d['mountpoint']}</td>
            <td style="padding:8px 14px;font-family:monospace">{d['percent']}%</td></tr>"""

    html_body = f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#0f172a;font-family:'Segoe UI',sans-serif;color:#e2e8f0">
<div style="max-width:600px;margin:40px auto;background:#1e293b;border-radius:12px;overflow:hidden;border:1px solid #334155">

  <!-- Header -->
  <div style="background:#f43f5e;padding:24px 28px">
    <div style="font-size:11px;text-transform:uppercase;letter-spacing:2px;opacity:.85;margin-bottom:6px">System Alert</div>
    <div style="font-size:22px;font-weight:700">{count} Threshold{"s" if count != 1 else ""} Exceeded</div>
    <div style="font-size:13px;opacity:.8;margin-top:4px">{hostname} &nbsp;·&nbsp; {now}</div>
  </div>

  <!-- Alerts table -->
  <div style="padding:24px 28px 8px">
    <div style="font-size:11px;text-transform:uppercase;letter-spacing:1.5px;color:#64748b;margin-bottom:12px">Triggered Alerts</div>
    <table style="width:100%;border-collapse:collapse;background:#0f172a;border-radius:8px;overflow:hidden">
      <thead>
        <tr style="background:#1e293b">
          <th style="padding:10px 14px;text-align:left;font-size:11px;color:#64748b;text-transform:uppercase">Metric</th>
          <th style="padding:10px 14px;text-align:left;font-size:11px;color:#64748b;text-transform:uppercase">Value</th>
          <th style="padding:10px 14px;text-align:left;font-size:11px;color:#64748b;text-transform:uppercase">Limit</th>
          <th style="padding:10px 14px;text-align:left;font-size:11px;color:#64748b;text-transform:uppercase">Detail</th>
        </tr>
      </thead>
      <tbody>{alert_rows}</tbody>
    </table>
  </div>

  <!-- Current metrics -->
  <div style="padding:16px 28px 28px">
    <div style="font-size:11px;text-transform:uppercase;letter-spacing:1.5px;color:#64748b;margin-bottom:12px">Current Metrics</div>
    <table style="width:100%;border-collapse:collapse;background:#0f172a;border-radius:8px;overflow:hidden">
      <tbody>{metric_rows}</tbody>
    </table>
  </div>

  <!-- Footer -->
  <div style="padding:16px 28px;border-top:1px solid #334155;font-size:12px;color:#475569">
    Generated by system-monitor &nbsp;·&nbsp; {hostname}
  </div>
</div>
</body>
</html>"""

    return text_body, html_body


def send_email(alerts, metrics):
    """Send an alert email via SMTP."""
    if not SMTP_USER or not SMTP_PASSWORD or not EMAIL_TO:
        print("[ERROR] Email not configured. Set SMTP_USER, SMTP_PASSWORD, and EMAIL_TO.")
        return False

    hostname = os.uname().nodename
    count    = len(alerts)
    subject  = f"🚨 [{hostname}] {count} System Alert{'s' if count != 1 else ''} — {', '.join(a['type'] for a in alerts)}"

    text_body, html_body = build_email_body(alerts, metrics)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())
        print(f"[OK] Alert email sent to {EMAIL_TO}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")
        return False


# =============================================================================
#  MAIN
# =============================================================================

def run_check(verbose=True):
    """Run one check cycle. Returns True if any alerts were triggered."""
    now     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    metrics = get_metrics()
    alerts  = check_thresholds(metrics)

    if verbose:
        print(f"\n[{now}] CPU: {metrics['cpu']}%  RAM: {metrics['ram']}%  "
              + "  ".join(f"Disk {d['mountpoint']}: {d['percent']}%" for d in metrics["disks"]))

    if alerts:
        print(f"[{now}] ⚠  {len(alerts)} alert(s) triggered: "
              + ", ".join(f"{a['type']} {a['value']}" for a in alerts))
        send_email(alerts, metrics)
        return True
    else:
        if verbose:
            print(f"[{now}] ✓  All metrics within thresholds.")
        return False


def main():
    parser = argparse.ArgumentParser(description="System Monitor with Email Alerts")
    parser.add_argument("--loop", action="store_true",
                        help=f"Run continuously every {INTERVAL}s (Ctrl+C to stop)")
    parser.add_argument("--interval", type=int, default=INTERVAL,
                        help=f"Seconds between checks when using --loop (default: {INTERVAL})")
    parser.add_argument("--test-email", action="store_true",
                        help="Send a test alert email regardless of current metric values")
    args = parser.parse_args()

    if args.test_email:
        print("[INFO] Sending test alert email...")
        metrics = get_metrics()
        fake_alerts = [
            {"type": "CPU",  "value": "81%", "threshold": f"{CPU_THRESHOLD}%",
             "message": "This is a test alert — CPU threshold exceeded."},
            {"type": "RAM",  "value": "86%", "threshold": f"{RAM_THRESHOLD}%",
             "message": "This is a test alert — RAM threshold exceeded."},
        ]
        send_email(fake_alerts, metrics)
        return

    if args.loop:
        interval = args.interval
        print(f"[INFO] Running in loop mode (every {interval}s). Press Ctrl+C to stop.")
        try:
            while True:
                run_check()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[INFO] Stopped.")
    else:
        run_check()


if __name__ == "__main__":
    main()
