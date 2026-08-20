# Honeypot Kit

Educational SSH honeypot with modular hardware monitoring for Raspberry Pi.

Deploy in 15-20 minutes. Monitor attacks in real-time with OLED display, LED indicators, and push-button control.

⚠️ **Status:** Install script tested and working on RPi4 64-bit Debian Trixie. LED status indicators tested and working. OLED display implemented, awaiting hardware testing. See [Threat Model](docs/THREAT_MODEL.md) for design scope.

## What It Does

Captures and analyzes SSH login attempts and attacker behavior for learning and threat analysis.

**Honeypot Kit is great for:**
- Learning how attackers work and what they try
- Network monitoring and real-time attack visualization
- Security team training and exercises
- Home lab network protection
- Hands-on Raspberry Pi hardware projects

**Honeypot Kit is NOT for:**
- Stopping or blocking real attacks (it's educational, not a firewall)
- Protecting sensitive production systems
- Legal or forensic evidence collection
- Enterprise security solutions

This is a learning tool first, production monitoring second.

## Features

### Core Honeypot
- **Quick Setup:** 15-20 minute automated installation on Raspberry Pi 4
- **Cowrie SSH Honeypot:** Captures login attempts, commands, and attacker behavior on port 22
- **Automatic Health Checks:** Every 5 minutes, ensures honeypot stays running
- **Intelligent Logging:** 7-day automatic log rotation and cleanup
- **OPSEC Hardening:** Random hostname suggestion, hidden dashboard, firewall rules, time synchronization
- **Real-time Monitoring:** Live attack capture and analysis

### Hardware Modules (Optional)
- **OLED Display:** Real-time IP address, attack count, active sessions, disk usage, uptime
- **LED Status Indicators:** Color-coded status with flash patterns (Green=healthy, Yellow=warning/activity, Red=error)
- **Push Button Control ($1):** Safe shutdown without SSH access

### CLI Tool
- `honeypot-kit status` - show hardware module configuration
- `honeypot-kit oled enable/disable/test/set-address/set-resolution`
- `honeypot-kit led enable/disable/test/set-pins`
- `honeypot-kit monitor start/stop/restart/status`
- `honeypot-kit update status/now/enable/disable`

### Reliability
- Auto-restart if honeypot fails
- Health monitoring and alerts
- Automatic log cleanup (never fills disk)
- Time synchronization (prevents OPSEC leaks)
- Optional weekly auto-updates for Honeypot Kit modules

## Hardware Requirements

### Minimum
- Raspberry Pi 4 (4GB RAM minimum)
- Micro SD card (64GB minimum)
- Power supply
- Ethernet cable

### Recommended (Production)
- Raspberry Pi 4 (8GB RAM)
- Micro SD card (256GB minimum)
- Ethernet adapter
- Case

### Optional Hardware Modules
- OLED display (SSD1306/SSD1315 I2C, 128x64) - ~$10-15
- LED traffic light module (built-in resistors) - ~$4-8
- Push button + resistor - ~$1-2

**Estimated Cost (as of 2026):**
- Core only: $85-125 (prices vary by supplier)
- With hardware modules: $100-150 (prices vary)

Note: Prices fluctuate due to chip shortages and supply chain. Check current pricing on electronics retailers.

## Architecture

```
Honeypot Kit on Raspberry Pi
├── Cowrie SSH Honeypot
│   ├── Listens on port 22
│   ├── Logs all SSH attempts
│   └── Records attacker commands
├── Hardware Monitor Daemon
│   ├── Reads Cowrie JSON log in real time
│   ├── Drives OLED display (Pillow image abstraction)
│   └── Drives LED indicators (flash patterns per state)
├── Health Monitor
│   ├── Checks every 5 minutes
│   ├── Auto-restarts if needed
│   └── Monitors disk/memory
├── Hardware Modules (Optional)
│   ├── OLED display (real-time stats)
│   ├── LED indicators (visual status)
│   └── Button control (safe shutdown)
└── Firewall & Security
    ├── UFW hardening
    ├── Hidden monitoring dashboard
    └── NTP time synchronization
```

## Quick Start

```bash
# On Raspberry Pi
wget https://raw.githubusercontent.com/ericburnsonline/honeypot-kit/main/install-honeypot.sh
sudo bash install-honeypot.sh
```

Follow prompts for network interface, hostname, SSH port, and optional auto-updates.

## Enabling Hardware Modules

After install, use the CLI to enable and test hardware:

```bash
# OLED display
honeypot-kit oled set-address 0x3C   # find address with: i2cdetect -y 1
honeypot-kit oled enable
honeypot-kit oled test
honeypot-kit monitor start

# LED traffic light module
honeypot-kit led set-pins --red 17 --yellow 27 --green 22
honeypot-kit led enable
honeypot-kit led test
honeypot-kit monitor start
```

## Integrations

Integrations follow a three-stage model: Stage 1 (overview doc), Stage 2 (working installable integration), Stage 3 (DIY guide).

| Integration | Stage 1 | Stage 2 | Stage 3 |
|-------------|---------|---------|---------|
| Grafana     | ✅ [docs/integrations/grafana.md](docs/integrations/grafana.md) | Planned | Planned |
| Alerting (PagerDuty/Slack) | Planned | Planned | Planned |
| Kafka / Redpanda | Planned | Planned | Planned |
| Claude AI analysis | Planned | Planned | Planned |
| SIEM (Wazuh) | Planned | Planned | Planned |

## Roadmap

**Phase 1 (Now):** Core honeypot + hardware modules + CLI
**Phase 2:** Grafana dashboard for visualization
**Phase 3:** Alerting integrations
**Phase 4:** Kafka event streaming + Claude AI analysis
**Phase 5+:** Kubernetes and multi-honeypot coordination

## License

**Open Source:** GNU Affero General Public License v3 (AGPL v3)

Free for open source and educational use.

**Commercial Licensing:** Available for proprietary use

Contact: burns@interhouse.com for commercial licensing inquiries.

See LICENSE file for complete terms.

## Attribution

Built with:
- **Cowrie SSH Honeypot** (GPL v2)
- **Python** (PSF License)
- **Click** (BSD License)
- **Pillow** (HPND License)
- **Adafruit CircuitPython SSD1306** (MIT License)

See NOTICE file for complete attribution.

## Next Steps

1. **Get a Raspberry Pi 4** (4GB minimum)
2. **Flash Raspberry Pi OS 64-bit (Debian Trixie)**
3. **Run the install script**
4. **Optionally connect OLED display and LED module**

---

**Educational. Open source. Hardware-friendly.**

🍯 Happy hunting!
