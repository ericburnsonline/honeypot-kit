# Honeypot Kit

Educational SSH honeypot with modular hardware monitoring for Raspberry Pi.

Deploy in 15-20 minutes. Monitor attacks in real-time with OLED display, LED indicators, and a full-screen terminal interface.

✅ **Status:** Install script tested and working on RPi4 64-bit Debian Trixie. OLED display and LED status indicators tested and working on physical hardware. OpenAI session analysis integration working. See [Threat Model](docs/THREAT_MODEL.md) for design scope.

---

## What It Does

Captures and analyzes SSH login attempts and attacker behavior for learning and threat analysis.

**Honeypot Kit is great for:**
- Learning how attackers work and what they try
- Network monitoring and real-time attack visualization
- Security team training and demo environments
- Home lab network protection
- Hands-on Raspberry Pi hardware projects
- Solutions Engineers building portfolio integrations with SaaS products

**Honeypot Kit is NOT for:**
- Stopping or blocking real attacks (it's educational, not a firewall)
- Protecting sensitive production systems
- Legal or forensic evidence collection
- Enterprise security solutions

This is a learning tool first, production monitoring second.

---

## Features

### Core Honeypot
- **Quick Setup:** 15-20 minute automated installation on Raspberry Pi 4
- **Cowrie SSH Honeypot:** Captures login attempts, commands, and attacker behavior on port 22
- **Automatic Health Checks:** Every 5 minutes, ensures honeypot stays running
- **Intelligent Logging:** 7-day automatic log rotation and cleanup
- **OPSEC Hardening:** Random hostname suggestion, firewall rules, time synchronization
- **Modular Smoke Test:** Extensible test framework with per-integration test fragments

### Hardware Modules (Optional)
- **OLED Display:** Real-time IP address, attack count, active sessions, disk usage, uptime
- **LED Status Indicators:** Color-coded status with flash patterns (Green=healthy, Yellow=active session, Red=login alert)
- **Display abstraction layer:** Pillow Image as universal render target - new display drivers are drop-in

### Interface
- **TUI:** Full-screen terminal interface (`hk`) - status dashboard, session browser, hardware controls, log viewer
- **CLI:** `honeypot-kit` command for scripting and automation
- **Session Browser:** Browse Cowrie sessions, view commands, send to AI for analysis

### AI Analysis
- **OpenAI integration:** Converts raw Cowrie sessions into structured security analysis
- **Structured output:** Intent classification, MITRE ATT&CK mapping, indicators, educational explanation
- **Prompt injection protection:** Attacker-controlled text treated as untrusted data
- **Cost estimate before API call:** Shows token count and cost, asks for confirmation
- **Cached results:** Analyzed sessions never sent to API twice

### Reliability
- Auto-restart if honeypot fails
- Health monitoring and alerts
- Automatic log cleanup (never fills disk)
- Time synchronization (prevents OPSEC leaks)
- Optional weekly auto-updates for Honeypot Kit modules

---

## Hardware Requirements

### Minimum
- Raspberry Pi 4 (4GB RAM minimum)
- Micro SD card (64GB minimum)
- USB-C power supply (5V 3A)
- Ethernet cable

### Optional Hardware Modules
- OLED display (SSD1306/SSD1315 I2C, 128x64) - ~$10-15
- LED traffic light module (built-in resistors) - ~$4-8

See [docs/HARDWARE_SETUP.md](docs/HARDWARE_SETUP.md) for wiring diagrams and GPIO pin assignments.

**Estimated Cost (as of 2026):**
- Core only: $65-90
- With hardware modules: $80-115

---

## Quick Start

```bash
# On Raspberry Pi
wget https://raw.githubusercontent.com/ericburnsonline/honeypot-kit/main/install-honeypot.sh
sudo bash install-honeypot.sh
```

Follow prompts for network interface, hostname, SSH port, and optional auto-updates. Installation takes approximately 11 minutes unattended after the prompts.

After install, launch the TUI:

```bash
hk
```

Or use the CLI directly:

```bash
honeypot-kit status
```

---

## Enabling Hardware Modules

```bash
# OLED display
sudo honeypot-kit oled set-address 0x3C   # find address: i2cdetect -y 1
sudo honeypot-kit oled set-resolution 128x64
sudo honeypot-kit oled enable
sudo honeypot-kit oled test
sudo honeypot-kit monitor start

# LED traffic light module
sudo honeypot-kit led set-pins --red 17 --yellow 27 --green 22
sudo honeypot-kit led enable
sudo honeypot-kit led test
sudo honeypot-kit monitor start
```

---

## CLI Reference

```bash
honeypot-kit status                        # show hardware config and monitor state
honeypot-kit oled enable/disable/test      # manage OLED display
honeypot-kit oled set-address 0x3C         # set I2C address
honeypot-kit oled set-resolution 128x64    # set display resolution
honeypot-kit led enable/disable/test       # manage LED indicators
honeypot-kit led set-pins --red --yellow --green  # assign GPIO pins
honeypot-kit led clear-alert               # clear login history alert
honeypot-kit monitor start/stop/restart/status    # manage hardware daemon
honeypot-kit update status/now/enable/disable     # manage auto-updates
honeypot-kit integration list              # show available integrations
honeypot-kit integration install <name>    # install an integration
honeypot-kit integration status            # show installed integrations
honeypot-kit ai status                     # OpenAI integration status
honeypot-kit ai test                       # test API connection
honeypot-kit ai analyze --latest           # analyze most recent session
honeypot-kit ai history                    # show recent analyses
honeypot-kit menu                          # launch TUI
```

---

## Integrations

Integrations follow a three-stage model: Stage 1 (overview doc), Stage 2 (working installable integration via CLI), Stage 3 (DIY guide).

| Integration | Stage 1 | Stage 2 | Stage 3 |
|-------------|---------|---------|---------|
| OpenAI session analysis | ✅ [docs/integrations/openai.md](docs/integrations/openai.md) | ✅ `honeypot-kit integration install openai` | Planned |
| Grafana dashboards | ✅ [docs/integrations/grafana.md](docs/integrations/grafana.md) | Planned | Planned |
| Alerting (PagerDuty/Slack) | Planned | Planned | Planned |
| Sentry observability | Planned | Planned | Planned |
| Kafka / Redpanda | Planned | Planned | Planned |
| SIEM (Wazuh) | Planned | Planned | Planned |
| Claude AI analysis | Planned | Planned | Planned |

---

## Architecture

```
Honeypot Kit on Raspberry Pi
├── Cowrie SSH Honeypot (port 22)
│   ├── Captures login attempts and attacker commands
│   └── Writes structured JSON events to cowrie.json
├── Hardware Monitor Daemon
│   ├── Reads Cowrie JSON log in real time
│   ├── Drives OLED display (Pillow image abstraction)
│   └── Drives LED indicators (flash patterns per state)
├── TUI (hk)
│   ├── Status dashboard, session browser, log viewer
│   └── Launches from: hk or honeypot-kit menu
├── CLI (honeypot-kit)
│   ├── Hardware module management
│   ├── Integration manager
│   └── AI analysis commands
├── Integration Framework
│   ├── Manifest-driven (integrations/manifest.json)
│   ├── Install via CLI (honeypot-kit integration install)
│   └── Modular smoke test fragments per integration
└── Health + Auto-update
    ├── 5-minute health check cron
    └── Weekly module update timer
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/HARDWARE_SETUP.md](docs/HARDWARE_SETUP.md) | Wiring, GPIO pins, I2C setup, LED states |
| [docs/TESTING.md](docs/TESTING.md) | Post-install acceptance checklist |
| [docs/SE_GUIDE.md](docs/SE_GUIDE.md) | Using this project as an SE portfolio and learning platform |
| [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) | Design scope and security boundaries |
| [docs/integrations/openai.md](docs/integrations/openai.md) | OpenAI integration overview and API key setup |
| [docs/integrations/grafana.md](docs/integrations/grafana.md) | Grafana integration overview |

---

## Roadmap

**Phase 1 (Now):** Core honeypot + hardware modules + CLI + TUI + OpenAI analysis
**Phase 2:** Grafana dashboards for attack visualization
**Phase 3:** Alerting integrations (PagerDuty, Slack)
**Phase 4:** Sentry observability + Temporal workflows
**Phase 5:** Kafka event streaming + Claude AI analysis
**Phase 6+:** Kubernetes multi-honeypot coordination

---

## License

**Open Source:** GNU Affero General Public License v3 (AGPL v3)

Free for open source and educational use.

**Commercial Licensing:** Available for proprietary use.
Contact: burns@interhouse.com

See [LICENSE](LICENSE) for complete terms.

---

## Attribution

Built with:
- **Cowrie SSH Honeypot** (GPL v2)
- **Python** (PSF License)
- **Click** (BSD License)
- **Pillow** (HPND License)
- **Adafruit CircuitPython SSD1306** (MIT License)
- **OpenAI Python SDK** (MIT License)

See [NOTICE](NOTICE) for complete attribution.

---

**Educational. Open source. Hardware-friendly.**

🍯 Happy hunting!
