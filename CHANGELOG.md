# Changelog

All notable changes to Honeypot Kit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## Unreleased

### In Progress
- Hardware module testing (OLED, LED) on physical hardware
- Grafana integration Stage 2 (working installable integration)
- data-pipeline.md (shared Prometheus/Loki/InfluxDB infrastructure doc)

### Planned (Phase 2-5)
- Grafana dashboard for attack visualization
- Alerting integration (Alertmanager + Slack/PagerDuty)
- Kafka event streaming integration
- Claude AI analysis of attack patterns
- SIEM integration (Wazuh)
- Kubernetes orchestration support
- Multi-honeypot coordination

---

## [0.3.0] - 2026-08-20

### Added
- `modules/cli.py` - CLI tool source (`honeypot-kit` command), downloaded
  by install script at install time
- `modules/monitor.py` - hardware monitor daemon, drives OLED display and
  LED indicators continuously from live Cowrie data
- `docs/integrations/grafana.md` - Stage 1 Grafana integration overview:
  recommended stack (Prometheus + Grafana), software requirements, costs,
  planned dashboards, and security considerations
- Hardware monitor daemon features:
  - Reads Cowrie JSON log in real time (attack count, rate, active sessions,
    last attacker IP)
  - Pillow Image as universal render target - display drivers are pluggable
  - Two OLED layouts: small (128x32/128x64) and square (128x128)
  - LED flash patterns per state: solid, slow flash (1s), fast flash (0.25s)
  - Startup sequence flashes all three LEDs to confirm hardware is alive
  - Graceful shutdown on SIGTERM/SIGINT
- LED state table: healthy, active session, high attack rate, warning,
  Cowrie down, critical error - each with distinct flash pattern
- Auto-update system: optional weekly updates for Honeypot Kit modules
  (cli.py, monitor.py, integrations) - never touches Cowrie or system packages
- `honeypot-update.sh` - SHA256 checksum comparison; replaces files only
  when changed; restarts monitor if monitor.py updated; logs all activity
- systemd timer pair: weekly Sunday at 03:00

### Changed
- Install script now downloads CLI and monitor from GitHub at install time
  rather than embedding them as heredocs
- CLI gains: `honeypot-kit monitor start/stop/restart/status`
- CLI gains: `honeypot-kit update status/now/enable/disable`
- Smoke test heredoc escaping bug fixed
- Smoke test adds CLI check and auto-update timer check
- Install prompt added for auto-update preference
- OLED supported resolutions expanded: 128x64, 128x32, 96x16, 128x128

### Known Issues
- LED status indicators tested and working on physical hardware
- OLED display implemented, not yet tested on physical hardware -
  use `honeypot-kit oled test` as first step when display is connected

---

## [0.2.0] - 2026-08-16

### Added
- `install-honeypot.sh` - first working install script, confirmed on RPi4
  64-bit Debian Trixie (2026-06-18)
- Cowrie SSH honeypot deployed on port 22 via authbind
- Real SSH auto-configured to user-selected port (default 2222) with
  validation (range, in-use check, well-known port warning)
- Random OPSEC-friendly hostname suggestion from realistic pool with
  user override
- Systemd service with forking type, PIDFile tracking, and
  network-online.target dependency
- authbind configured automatically so Cowrie can bind to port 22
  as unprivileged user
- Smoke test script
- Health check script running every 5 minutes via cron
- nmap installed for local port verification
- Reboot prompt at end of install with warning if declined
- Unattended install timing displayed at completion
- Invocation check - detects if not run as `sudo bash` and exits cleanly

---

## [0.1.0] - 2026-07-13

### Added - July 13, 2026
- Code of Conduct establishing community standards and inclusive environment
- Clear expectations for module contributions (substance over marketing)
- Reporting and enforcement procedures for code of conduct violations

### Added - July 3, 2026
- Contributing Guidelines with clear pathways for community contribution
- Six concrete ways to contribute (testing, hardware design, docs,
  dashboards, modules, SE perspective)
- Development workflow and code style expectations
- Licensing requirements and recognition process

### Added - June 16, 2026
- Public GitHub repository established
- GNU Affero General Public License v3 (AGPL v3) with dual licensing support
- Comprehensive README with project vision, features, hardware requirements
- Threat Model documenting project scope and design boundaries
- Attribution and compliance notices for Cowrie (GPL v2) and dependencies
- .gitignore configured for Python projects

---

## Links

- [GitHub Repository](https://github.com/ericburnsonline/honeypot-kit)
- [Contributing Guidelines](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Threat Model](docs/THREAT_MODEL.md)
- [License](LICENSE)
