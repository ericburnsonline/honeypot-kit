# Changelog

All notable changes to Honeypot Kit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## Unreleased

### In Progress
- Hardware module implementations (OLED, LED, Button)
- Dashboard integration framework
- Smoke test script bug fix (line 32 heredoc escaping issue)

### Planned (Phase 2-5)
- Grafana dashboard for attack visualization
- Kafka event streaming integration
- Claude AI analysis of attack patterns
- Kubernetes orchestration support
- Multi-honeypot coordination

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
- Smoke test script (known issue: line 32 bug to be fixed in next commit)
- Health check script running every 5 minutes via cron
- nmap installed for local port verification
- Reboot prompt at end of install with warning if declined
- Unattended install timing displayed at completion
- Invocation check - detects if not run as `sudo bash` and exits cleanly

### Known Issues
- smoke-test.sh line 32 fails due to heredoc escaping bug - Cowrie
  and all other functionality unaffected

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
