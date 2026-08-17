# Honeypot Kit

Educational SSH honeypot with modular hardware monitoring for Raspberry Pi.

Deploy in 15-20 minutes. Monitor attacks in real-time with OLED display, LED indicators, and push-button control.

⚠️ **Status:** Install script tested and working on RPi4 64-bit Debian Trixie. Hardware modules in development. See [Threat Model](docs/THREAT_MODEL.md) for design scope.

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
- **Cowrie SSH Honeypot:** Captures login attempts, commands, and attacker behavior
- **Automatic Health Checks:** Every 5 minutes, ensures honeypot stays running
- **Intelligent Logging:** 7-day automatic log rotation and cleanup
- **OPSEC Hardening:** Hidden dashboard, firewall rules, time synchronization
- **Real-time Monitoring:** Live attack capture and analysis

### Hardware Modules (Optional)
- **OLED Display ($10):** Real-time IP address, event count, CPU/RAM usage on 128x64 display
- **LED Status Indicators ($4):** Color-coded status (Green=healthy, Yellow=warning, Red=error)
- **Push Button Control ($1):** Safe shutdown without SSH access

### Reliability
- Auto-restart if honeypot fails
- Health monitoring and alerts
- Automatic log cleanup (never fills disk)
- Time synchronization (prevents OPSEC leaks)

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
- OLED display (SSD1306 I2C) - ~$10-15
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
├── Health Monitor
│   ├── Checks every 5 minutes
│   ├── Auto-restarts if needed
│   └── Monitors disk/memory
├── Hardware Modules (Optional)
│   ├── OLED display (real-time status)
│   ├── LED indicators (visual feedback)
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

Follow prompts for network interface, hostname, and firewall configuration.

## Roadmap

**Phase 1 (Now):** Core honeypot + hardware modules
**Phase 2:** Grafana dashboard for visualization
**Phase 3:** Kafka event streaming
**Phase 4:** Claude AI analysis
**Phase 5+:** Kubernetes and multi-honeypot coordination

18 total modules planned. See documentation as project grows.

## License

**Open Source:** GNU Affero General Public License v3 (AGPL v3)

Free for open source and educational use.

**Commercial Licensing:** Available for proprietary use

Contact: burns@interhouse.com for commercial licensing inquiries.

See LICENSE file for complete terms.

## Getting Started

Documentation is added with each commit as the project grows.

Check back regularly to see:
- Installation guides
- Setup tutorials
- Troubleshooting help
- Module documentation
- OPSEC details
- Maintenance procedures

## Attribution

Built with:
- **Cowrie SSH Honeypot** (GPL v2)
- **Python** (PSF License)
- **FastAPI** (MIT License)

See NOTICE file for complete attribution.

## Next Steps

1. **Get a Raspberry Pi 4** (4GB minimum)
2. **Flash Raspberry Pi OS 64-bit (Debian Trixie)**
3. **Watch this repository** for documentation updates
4. **Follow installation guide** when available

---

**Educational. Open source. Hardware-friendly.**

🍯 Happy hunting!
