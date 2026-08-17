# Grafana Integration

**Stage 1 of 3 - Overview and Planning**

This document covers what a Grafana integration for Honeypot Kit would look like,
what software is involved, and what it would cost. A working installable integration
(Stage 2) and a DIY guide for writing your own (Stage 3) will follow.

---

## What This Integration Does

Connects Cowrie's attack logs to Grafana, giving you live dashboards that show:

- Attack attempts over time (per hour, per day, per week)
- Top source IP addresses and countries of origin
- Most common usernames and passwords attempted
- Commands attackers run after a successful fake login
- Active session count in real time
- Honeypot health metrics (uptime, disk, memory)

The result is a visual, real-time picture of who is hitting your honeypot and
what they are trying to do.

---

## Recommended Stack

There are several ways to connect Cowrie to Grafana. The recommended approach
for a Raspberry Pi is **Prometheus + Grafana** because both run comfortably
within the Pi's memory budget and the entire stack is free and open source.

```
Cowrie JSON logs
      |
      v
 Python exporter        (small script, ships with this integration)
      |
      v
  Prometheus             (scrapes the exporter every 15 seconds)
      |
      v
   Grafana               (queries Prometheus, renders dashboards)
```

A second supported option is **Loki + Grafana**, which is better suited
to raw log exploration rather than time-series metrics. Both options are
documented in Stage 2.

---

## Software Required

### Grafana
- **What it is:** The dashboard and visualization layer. Runs as a web service,
  accessed via browser.
- **Cost:** Free (OSS edition). No account required for local use.
- **Get it:** https://grafana.com/grafana/download?platform=arm
- **Pi note:** Use the ARM64 build for Raspberry Pi OS 64-bit.
- **Port:** Runs on port 3000 by default.

### Prometheus
- **What it is:** A time-series database that scrapes metrics from exporters
  on a schedule and stores them for querying.
- **Cost:** Free and open source.
- **Get it:** https://prometheus.io/download/ (look for the `linux-arm64` build)
- **Port:** Runs on port 9090 by default.

### Cowrie JSON log exporter
- **What it is:** A small Python script (ships with this integration) that
  reads Cowrie's JSON log file and exposes metrics on an HTTP endpoint that
  Prometheus scrapes.
- **Cost:** Free - part of Honeypot Kit.
- **No separate download required.**

### Optional - Loki + Promtail (alternative to Prometheus)
- **What it is:** Loki is Grafana's own log aggregation system. Promtail
  ships logs to Loki. Grafana queries Loki directly for log-based dashboards.
- **Cost:** Free and open source.
- **Get it:** https://grafana.com/oss/loki/
- **Best for:** Exploring raw log lines rather than numeric metrics.

### Optional - GeoIP database (for country mapping)
- **What it is:** Maps attacker IP addresses to countries on a world map panel.
- **Cost:** Free tier available (MaxMind GeoLite2). Requires a free account.
- **Get it:** https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
- **Note:** The free database updates monthly. The paid MaxMind GeoIP2 database
  updates more frequently but is not required for most use cases.

---

## Resource Requirements

Running the full stack on a Raspberry Pi 4 adds approximately:

| Component          | RAM       | Disk      |
|--------------------|-----------|-----------|
| Grafana            | ~150 MB   | ~300 MB   |
| Prometheus         | ~50 MB    | grows with retention (default 15 days) |
| Cowrie exporter    | ~20 MB    | minimal   |
| **Total added**    | ~220 MB   | ~500 MB+  |

A Pi 4 with 4GB RAM handles this comfortably alongside Cowrie. A 2GB Pi 4
is workable but tight. A Pi 3 is not recommended.

---

## Dashboards Planned for Stage 2

The working integration will ship with pre-built Grafana dashboards for:

- **Attack Timeline** - attempts per hour and per day with trend line
- **Top Attackers** - source IPs ranked by attempt count
- **Credential Analysis** - most tried usernames and passwords
- **Command Activity** - commands attackers run in fake shell sessions
- **World Map** - geographic origin of attacks (requires GeoIP, optional)
- **Honeypot Health** - uptime, Cowrie process status, disk and memory usage

Dashboards are exported as JSON and imported into Grafana with one click.

---

## Security Considerations

Grafana should **never** be exposed directly to the internet on this system.
The honeypot's public face is Cowrie on port 22. Grafana runs on port 3000
and should only be accessible via SSH tunnel:

```bash
ssh -p <your-ssh-port> -L 3000:localhost:3000 pi@<honeypot-ip>
```

Then open `http://localhost:3000` in your browser. The Honeypot Kit firewall
rules block port 3000 from external access by default.

Prometheus (port 9090) should also remain internal only.

---

## What's Next

- **Stage 2** - Working integration installable via the Honeypot Kit CLI:
  ```bash
  honeypot-kit integration install grafana
  ```
  Adds Grafana CLI subcommand, installs the stack, imports dashboards,
  and adds a Grafana check to the smoke test.

- **Stage 3** - DIY guide covering how the exporter works, how Prometheus
  scrapes metrics, how to build custom Grafana panels, and how to write
  your own integration module for Honeypot Kit.

---

## Links

- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana OSS Download](https://grafana.com/grafana/download?platform=arm)
- [Prometheus Download](https://prometheus.io/download/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [MaxMind GeoLite2](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data)
- [Cowrie JSON log format](https://cowrie.readthedocs.io/en/latest/README.html)
