# 📡 System Monitor with Email Alerts

A lightweight Python script that monitors CPU, RAM, and disk usage — and sends an email alert when any threshold is crossed.

![Python](https://img.shields.io/badge/python-3.7%2B-blue)
![Platform](https://img.shields.io/badge/platform-Linux-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## How It Works

1. Collects CPU, RAM, and disk metrics using `psutil`
2. Compares each value against configurable thresholds
3. If any threshold is exceeded, sends an HTML email alert
4. Can run once (manual/cron) or continuously in loop mode

---

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/system-monitor.git
cd system-monitor
pip3 install psutil
```

Set your email credentials as environment variables:

```bash
export SMTP_USER="you@gmail.com"
export SMTP_PASSWORD="your_app_password"
export EMAIL_TO="admin@example.com"
```

Run:

```bash
python3 monitor.py
```

---

## Usage

```bash
python3 monitor.py                    # run once
python3 monitor.py --loop             # run every 60s
python3 monitor.py --loop --interval 30   # run every 30s
python3 monitor.py --test-email       # send a test alert email
```

---

## Thresholds

Edit the constants at the top of `monitor.py`:

```python
CPU_THRESHOLD  = 80   # percent
RAM_THRESHOLD  = 85   # percent
DISK_THRESHOLD = 90   # percent
```

---

## Cron Setup

Run every 5 minutes and log output:

```bash
crontab -e
```

```cron
*/5 * * * * /usr/bin/python3 /opt/system-monitor/monitor.py >> /var/log/system-monitor.log 2>&1
```

---

## Email Configuration

Uses Gmail SMTP with an [App Password](https://support.google.com/accounts/answer/185833).

| Variable | Description |
|---|---|
| `SMTP_USER` | Your Gmail address |
| `SMTP_PASSWORD` | Gmail App Password |
| `EMAIL_TO` | Alert recipient |
| `SMTP_HOST` | SMTP server (default: `smtp.gmail.com`) |
| `SMTP_PORT` | SMTP port (default: `587`) |

Store these in a `.env` file and load with `source .env` before running, or configure them directly in your cron environment.

---

## Requirements

```
psutil>=5.9.0
```

Install: `pip3 install psutil`

---

## Skills Demonstrated

- Python scripting and CLI design (`argparse`)
- System metrics collection (`psutil`)
- SMTP email with HTML formatting
- Threshold-based alerting logic
- Cron job integration
